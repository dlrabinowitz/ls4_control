# -*- coding: utf-8 -*-
#
# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2021-01-19
# @Filename: archon.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)
#
# @Author: David Rabinowitz (david.rabinowitz@yale.edu)
# @Date: 2024-01-16
# @Filename: ls4_controller.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)
#
#
# This is an extension of the controller.py in sdss-archon
# distribution (on github)

from __future__ import annotations

import asyncio
import configparser
import io
import os
import re
import warnings
import time
import sys
from collections.abc import AsyncIterator

from typing import Any, Callable, Iterable, Literal, Optional, cast, overload

import numpy
import threading
from archon.controller.ls4_device import LS4_Device
from archon.controller.ls4_sync_io import LS4_SyncIO

from archon import config as lib_config
from archon import log
from archon.controller.command import ArchonCommand, ArchonCommandStatus
from archon.controller.maskbits import ArchonPower, ControllerStatus, ModType
from archon.exceptions import (
    ArchonControllerError,
    ArchonControllerWarning,
    ArchonUserWarning,
)

from . import MAX_COMMAND_ID, MAX_CONFIG_LINES, FOLLOWER_TIMEOUT_MSEC, \
              P100_SUPPLY_VOLTAGE, N100_SUPPLY_VOLTAGE, AMPS_PER_CCD, \
              CCDS_PER_QUAD, STATUS_LOCK_TIMEOUT


__all__ = ["LS4Controller"]

class TimePeriod():
    """ useful for keeping track of time intervals required for processes"""

    def __init__(self):

        self.start_time = 0.0
        self.end_time = 0.0
        self.period = 0.0

    def start(self):

        self.start_time=time.time()
        self.end_time = self.start

    def end(self):

        self.end_time = time.time()
        self.period = self.end_time-self.start_time

class LS4Controller(LS4_Device):
    """Talks to an Archon controller over TCP/IP.

    Parameters
    ----------
    name
        A name identifying this controller.
    host
        The hostname of the Archon.
    local_addr
        The (ip address,port) of the network interface  and port to use for connections (optional)
    port
        The port on which the Archon listens to incoming connections.
        Defaults to 4242.
    config
        Configuration data. Otherwise uses default configuration.
    """

    def __init__(
        self,
        name: str,
        host: str,
        local_addr: tuple = ('127.0.0.1',4242),
        port: int = 4242,
        config: dict | None = None,
        param_args: list[dict] | None = None,
        command_args: list[dict] | None = None,
        ls4_events: LS4_Events | None = None,
        ls4_logger: LS4_Logger | None = None,
        fake: bool | None = None,
        timing = None,
        notifier: Optional[Callable[[str], None]] = None,
    ):

        assert param_args is not None, "param_args are not specified"
        assert command_args is not None, "command_args are not specified"
        assert ls4_events is not None, "ls4_events are not specified"

        self.notifier = notifier
        self.leader = False
        self.prefix = "follow %s" % name
        if ls4_logger is None:
           self.ls4_logger = LS4_Logger(name=name)
        else:
           self.ls4_logger=ls4_logger

        self.info = self.ls4_logger.info
        self.debug = self.ls4_logger.debug
        self.warn= self.ls4_logger.warn
        self.error= self.ls4_logger.error
        self.critical= self.ls4_logger.critical

        if fake is not None:
           self.fake_controller = fake
           self.host = host
           self.port = port
           self.local_addr=local_addr
           self.fake_count = 0
           self.fake_data = None
           self.fake_conf={}
           self.fake_conf['bytes_per_pixel']=2
           self.fake_conf['data_type']=numpy.uint16
           self.fake_conf['n_amps']=AMPS_PER_CCD*CCDS_PER_QUAD

        else:
           self.fake_controller = False

        #self.add_logger(info=info, error=error, debug=debug, warn = warn)

        self.info("\n\tname: %s    host: %s    port: %d    local_addr: %s    fake: %s" %\
             (name,host,port,local_addr,fake))

        self.__running_commands: dict[int, ArchonCommand] = {}
        self._id_pool = set(range(MAX_COMMAND_ID))
        LS4_Device.__init__(self, name=name, host=host, port=port, local_addr=local_addr,
                    ls4_logger=self.ls4_logger)

        self.name = name
        self._status: ControllerStatus = ControllerStatus.UNKNOWN
        self.__status_event = asyncio.Event()

        self._binary_reply: Optional[bytearray] = None

        self.auto_flush: bool | None = None

        self.parameters: dict[str, int] = {}

        self.current_window: dict[str, int] = {}
        self.default_window: dict[str, int] = {}

        self.config = config or lib_config
        self.acf_file: str | None = None
        self.acf_config: configparser.ConfigParser | None = None

        # TODO: asyncio recommends using asyncio.create_task directly, but that
        # call get_running_loop() which fails in iPython.
        self._job = asyncio.get_event_loop().create_task(self.__track_commands())

        self.frame=None
      
        # addition by D. Rabinowitz follow here

        if "timeouts" not in self.config:
            self.config["timeouts"]={}

        self.config["timeouts"].update(\
            {"controller_connect": 5,\
            "write_config_timeout": 2,\
            "write_config_delay": 0.0001,\
            "expose_timeout": 2,\
            "readout_expected": 40,\
            "readout_max": 60,\
            "fetching_expected": 5,\
            "fetching_max": 10,\
            "flushing": 8.2,\
            "fast_flushing": 2.2,\
            "pneumatics": 1.5,\
            "purge": 0.2})

        if "supply voltages" not in self.config:
            self.config["supply voltages"]={}

        self.config["supply voltages"].update(\
               {"p5v_v":5.0,\
                "p6v_v":6.0,\
                "n6v_v":-6.0,\
                "p17v_v":17.0,\
                "n17v_v":-17.0,\
                "p35v_v":35.0,\
                #"n35v_v":-35.0,\
                # -35V line is not used, but registers as zero V ?
                "n35v_v":0.0,\
                #
                # Power Supply +/-100 lines changes to +/-50 v
                #"p100v_v":100.0,\
                #"n100v_v":-100.0\
                "p100v_v":P100_SUPPLY_VOLTAGE,\
                "n100v_v":N100_SUPPLY_VOLTAGE\
               })
             
        if "expose params" not in self.config:
            self.config["expose params"]={}

        self.config["expose params"].update(\
               {"date-obs":"0000-00-00T00:00:00",\
                "object": "TEST",\
                "obsmode": "TEST",\
                "imagetyp": "TEST",\
                "exptime": 0.0,\
                "focus": 0.0,\
                "tele-ra": 0.0,\
                "tele-dec": 0.0,\
                "chip-ra": 0.0,\
                "chip-dec": 0.0,\
                "equinox": 2000.0,\
                "lst": 0.0,\
                "ha": 0.0,\
                "filterna": "clear",\
                "filterid": "",\
                "frame": 0,\
                "read-per": 0.0,\
                "xbinning": 1,\
                "ybinning": 1,\
                "gain": 1.0,\
                "readnois": 0.0,\
                "ccdsec": "[1:1024,1:4096]",\
                "biassec": "[1024:1024,4096:4096]",\
                "bias": 0.0,\
                "ccdtemp": 0.0,\
                "fileroot": "",\
                "ujd": 0.0,\
                "fwhm": 0.0,\
                "sky": 0.0,\
                "skysigma": 0.0,\
                "zp": 0.0\
               })
             

        self.ls4_sync_io = LS4_SyncIO(name=self.name,ls4_events=ls4_events,
           param_args=param_args,command_args=command_args,ls4_logger = self.ls4_logger)
   
        self.set_sync_index=self.ls4_sync_io.set_sync_index
        self.set_sync=self.ls4_sync_io.set_sync

        if timing is not None:
           self.timing=timing
        else:
           self.timing={'expose':TimePeriod(),'readout':TimePeriod(),'fetch':TimePeriod()}

        # ned a mutex to lock self._status while changing status bits
        self.status_lock = threading.Lock()

    def set_lead(self, lead_flag: bool = False):
         self.leader = lead_flag
         self.prefix = "leader %s" % self.name
         if self.ls4_sync_io is not None:
            self.ls4_sync_io.set_lead(lead_flag)

    async def start(self, reset: bool = True, read_acf: bool = True):
        """Starts the controller connection. If ``reset=True``, resets the status."""

        await super().start()
        self.debug(f"Controller {self.name} connected at {self.host}.")

        if read_acf:
            self.debug(f"Retrieving ACF data from controller {self.name}.")
            config_parser, _ = await self.read_config()
            self.acf_config = config_parser
            self._parse_params()

        if reset:
            try:
                await self._set_default_window_params()
                await self.reset(sync_flag=False)
            except ArchonControllerError as err:
                warnings.warn(f"Failed resetting controller: {err}", ArchonUserWarning)

        return self

    @property
    def status(self) -> ControllerStatus:
        """Returns the status of the controller as a `.ControllerStatus` enum type."""

        try:
          if not self.status_lock.acquire(timeout=STATUS_LOCK_TIMEOUT):
             error_msg = "ERROR: failed to acquire status lock within %7.3f sec" %\
                  STATUS_LOCK_TIMEOUT
             self.warn(error_msg)
        except Exception as e:
          error_msg = "Exception acquiring status lock"
          self.warn(error_msg)

        state = self._status
        try:
          self.status_lock.release()
        except Exception as e:
          error_msg = "Exception releasing status lock"
          self.warn(error_msg)

        return state

    def is_exposing(self):
        return  self.status&ControllerStatus.EXPOSING

    def is_reading(self):
        return self.status&ControllerStatus.READING

    def is_fetching(self):
        return self.status&ControllerStatus.FETCHING

    def get_obsdate(self,tm=None):
        if tm is None:
           tm=time.gmtime()
        dt = "%04d-%02d-%02dT%02d:%02d:%05.2f" % \
              (tm.tm_year,tm.tm_mon,tm.tm_mday, tm.tm_hour,tm.tm_min,tm.tm_sec)
        return dt
        
    def update_status(
        self,
        bits: ControllerStatus | list[ControllerStatus],
        mode="on",
        notify=True,
    ):
        """Updates the status bitmask, allowing to turn on, off, or toggle a bit."""

        if not isinstance(bits, (list, tuple)):
            bits = [bits]

        # Check that we don't get IDLE and ACTIVE at the same time
        all_bits = ControllerStatus(0)
        for bit in bits:
            all_bits |= bit

        if (ControllerStatus.ACTIVE & all_bits) and (ControllerStatus.IDLE & all_bits):
            raise ValueError("Cannot set IDLE and ACTIVE bits at the same time.")

        status = self.status

        for bit in bits:
            if mode == "on":
                status |= bit
            elif mode == "off":
                status &= ~bit
            elif mode == "toggle":
                status ^= bit
            else:
                raise ValueError(f"Invalid mode '{mode}'.")

        try:
          if not self.status_lock.acquire(timeout=STATUS_LOCK_TIMEOUT):
             error_msg = "ERROR: failed to acquire status lock within %7.3f sec" %\
                  STATUS_LOCK_TIMEOUT
             self.warn(error_msg)
        except Exception as e:
          error_msg = "Exception acquiring status lock: %s" % e
          self.warn(error_msg)

        # Make sure that we don't have IDLE and ACTIVE states at the same time.
        if ControllerStatus.IDLE in bits:
            status &= ~ControllerStatus.ACTIVE

        if status & ControllerStatus.ACTIVE:
            status &= ~ControllerStatus.IDLE
        else:
            status |= ControllerStatus.IDLE

        # Handle incompatible power bits.
        if ControllerStatus.POWERBAD in bits:
            status &= ~(ControllerStatus.POWERON | ControllerStatus.POWEROFF)
        elif ControllerStatus.POWERON in bits or ControllerStatus.POWEROFF in bits:
            status &= ~ControllerStatus.POWERBAD
            if ControllerStatus.POWERON in bits:
                status &= ~ControllerStatus.POWEROFF
            else:
                status &= ~ControllerStatus.POWERON

        # Remove UNKNOWN bit if any other status has been set.
        if status != ControllerStatus.UNKNOWN:
            status &= ~ControllerStatus.UNKNOWN

        self._status = status
       
        try:
           self.status_lock.release()
        except Exception as e:
           error_msg = "Exception releasing status lock: %s" % e
           self.warn(error_msg)
      

        if notify:
            self.__status_event.set()

    async def yield_status(self) -> AsyncIterator[ControllerStatus]:
        """Asynchronous generator yield the status of the controller."""

        yield self.status  # Yield the status on subscription to the generator.
        while True:
            prev_status = self._status
            await self.__status_event.wait()
            if self.status != prev_status:
                yield self.status
            self.__status_event.clear()


    async def send_command(
        self,
        command_string: str,
        command_id: Optional[int] = None,
        sync_flag: bool | None = None,
        **kwargs,
    ) -> ArchonCommand:

        """Sends a command to the Archon.

        Parameters
        ----------
        command_string
            The command to send to the Archon. Will be converted to uppercase.
        command_id
            The command id to associate with this message. If not provided, a
            sequential, autogenerated one will be used.
        kwargs
            Other keyword arguments to pass to `.ArchonCommand`.
        """

        prefix = self.prefix
        error_msg = None

        if sync_flag is None:
           sync_flag = self.ls4_sync_io.sync_flag

        self.debug("sending command [%s] sync_flag: %s" %\
           (command_string,sync_flag))

        command_id = command_id or self._get_id()

        if command_id > MAX_COMMAND_ID or command_id < 0:
            raise ArchonControllerError(
                f"Command ID must be in the range [0, {MAX_COMMAND_ID:d}]."
            )

        command = ArchonCommand(
            command_string,
            command_id,
            controller=self,
            **kwargs,
        )

        self.__running_commands[command_id] = command

        # non-synchronous I/O
        if not sync_flag:
            self.debug("%s: asynchronously writing command [%s]" % (prefix,command.command_string))
            self.write(command.raw)

        # synchronous I/O
        else:

          # Here, The leader breezes through sync_prepare without waiting for events.
          # The followers, on the other hand, get held up until the  the leader later 
          # executes sync_update (below)

          self.debug("%s: preparing sync" % prefix)
          try:
            await self.ls4_sync_io.sync_prepare(param_args=None,\
                   command_args={'command_string':command_string,'command_id':command_id})
          except Exception as e:
            error_msg = "Exception preparing sync: %s" % e

          # After the leader has already proceeded to sync_update, the followers proceed to write the command and then 
          # update ls4_sync_io when they are done.
          #
          # Meanwhile, the leader updates ls4_sync_io before writing the command. It can not proceed
          # to write the command until the followers have all updated sync_io (after they have
          # all written the command).

          if error_msg is None:

            # The followers write the command here after leader update sync_io below.
            if not self.ls4_sync_io.leader:
              self.debug("%s: synchronously writing command [%s]" % (prefix,command.command_string))
              self.write(command.raw)

            # The followers wait here for leader to update sync_io. 
            # When the leader begins updating sync_io, it first allows the followers to proceed with their
            # own update to sync_io. The leader then waits until all the followers have completed
            # the update before it can proceed.
            self.debug("%s: updating sync" % prefix)
            try:
              await self.ls4_sync_io.sync_update(command_flag=True)
            except Exception as e:
              error_msg = "Exception updating sync: %s" % e
 
            # The leader writes the command here, after the followers have updated  sync_io.
            if self.ls4_sync_io.leader and not error_msg:
              self.debug("%s: synchronously writing command [%s]" % (prefix,command.command_string))
              self.write(command.raw)

            if not error_msg:
              self.debug("%s: verifying sync" % prefix)
              try:
                await self.ls4_sync_io.sync_verify(command_flag=True)
              except Exception as e:
                error_msg = "Exception verifying sync: %s" % e

        if error_msg is not None:
           self.error("%s: %s" % (prefix,error_msg))
           raise ArchonControllerError(f"Failed running {command_string}: %s" % error_msg)

        self.debug("done sending command [%s] sync_flag: %s" %\
           (command_string,sync_flag))
          
        return command

    def send_command(
        self,
        command_string: str,
        command_id: Optional[int] = None,
        sync_flag: bool | None = None,
        **kwargs,
    ) -> ArchonCommand:
        """Sends a command to the Archon.

        Parameters
        ----------
        command_string
            The command to send to the Archon. Will be converted to uppercase.
        command_id
            The command id to associate with this message. If not provided, a
            sequential, autogenerated one will be used.
        kwargs
            Other keyword arguments to pass to `.ArchonCommand`.
        """

        command_id = command_id or self._get_id()

        if command_id > MAX_COMMAND_ID or command_id < 0:
            raise ArchonControllerError(
                f"Command ID must be in the range [0, {MAX_COMMAND_ID:d}]."
            )

        command = ArchonCommand(
            command_string,
            command_id,
            controller=self,
            **kwargs,
        )
        self.__running_commands[command_id] = command

           
        self.write(command.raw)
        #self.debug(f"-> {command.raw}")
           
        return command

    async def send_many(
        self,
        cmd_strs: Iterable[str],
        max_chunk=100,
        timeout: Optional[float] = None,
    ) -> tuple[list[ArchonCommand], list[ArchonCommand]]:
        """Sends many commands and waits until they are all done.

        def send(command_str or times out, cancels any future command. Returns a list
        of done commands and a list failed commands (empty if all the commands
        have succeeded). Note that ``done+pending`` can be fewer than the length
        of ``cmd_strs``.

        The order in which the commands are sent and done is not guaranteed. If that's
        important, you should use `.send_command`.

        Parameters
        ----------
        cmd_strs
            List of command strings to send. The command ids are assigned automatically
            from available IDs in the pool.
        max_chunk
            Maximum number of commands to send at once. After sending, waits until all
            the commands in the chunk are done. This does not guarantee that
            ``max_chunk`` of commands will be running at once, that depends on the
            available command ids in the pool.
        timeout
            Timeout for each single command.

        """

        # Copy the strings so that we can pop them. Also reverse it because
        # we'll be popping items and we want to conserve the order.
        cmd_strs = list(cmd_strs)[::-1]
        done: list[ArchonCommand] = []

        while len(cmd_strs) > 0:
            pending: list[ArchonCommand] = []
            if len(cmd_strs) < max_chunk:
                max_chunk = len(cmd_strs)
            if len(self._id_pool) >= max_chunk:
                cmd_ids = (self._get_id() for __ in range(max_chunk))
            else:
                cmd_ids = (self._get_id() for __ in range(len(self._id_pool)))
            for cmd_id in cmd_ids:
                cmd_str = cmd_strs.pop()
                cmd = self.send_command(cmd_str, command_id=cmd_id, timeout=timeout)
                pending.append(cmd)
            done_cmds: list[ArchonCommand] = await asyncio.gather(*pending)
            if all([cmd.succeeded() for cmd in done_cmds]):
                done += done_cmds
                for cmd in done_cmds:
                    self._id_pool.add(cmd.command_id)
            else:
                failed: list[ArchonCommand] = []
                for cmd in done_cmds:
                    if cmd.succeeded():
                        done.append(cmd)
                    else:
                        failed.append(cmd)
                return done, failed

        return (done, [])

    async def send_and_wait(
        self,
        command_string: str,
        raise_error: bool = True,
        **kwargs,
    ):
        """Sends a command to the controller and waits for it to complete.

        Parameters
        ----------
        command_string
            The command to send to the Archon. Will be converted to uppercase.
        raise_error
            Whether to raise an error if the command fails. If `False`, a
            warning will be issued.
        kwargs
            Other arguments to be sent to `.send_command`.

        """

        command_string = command_string.upper()

        command = await self.send_command(command_string, **kwargs)

        if not command.succeeded():
            if raise_error:
                self.update_status(ControllerStatus.ERROR)
                raise ArchonControllerError(f"Failed running {command_string}.")
            else:
                warnings.warn(f"Failed running {command_string}.", ArchonUserWarning)

    async def process_message(self, line: bytes) -> None:
        """Processes a message from the Archon and associates it with its command."""

        match = re.match(b"^[<|?]([0-9A-F]{2})", line)
        if match is None:
            warnings.warn(
                f"Received invalid reply {line.decode()}",
                ArchonControllerWarning,
            )
            return

        command_id = int(match[1], 16)
        if command_id not in self.__running_commands:
            warnings.warn(
                f"Cannot find running command for {line}",
                ArchonControllerWarning,
            )
            return

        self.__running_commands[command_id].process_reply(line)

    async def stop(self):
        """Stops the client and cancels the command tracker."""

        self._job.cancel()
        await super().stop()

    async def get_system(self) -> dict[str, Any]:
        """Returns a dictionary with the output of the ``SYSTEM`` command."""

        cmd = await self.send_command("SYSTEM", timeout=5)
        if not cmd.succeeded():
            error = cmd.status == ArchonCommandStatus.TIMEDOUT
            raise ArchonControllerError(
                f"Command STATUS finished with status {cmd.status.name!r}",
                set_error_status=error,
            )

        keywords = str(cmd.replies[0].reply).split()
        system = {}
        for key, value in map(lambda k: k.split("="), keywords):
            system[key.lower()] = value
            if match := re.match(r"^MOD([0-9]{1,2})_TYPE", key, re.IGNORECASE):
                name_key = f"mod{match.groups()[0]}_name"
                system[name_key] = ModType(int(value)).name

        return system

    async def get_device_status(self, update_power_bits: bool = True) -> dict[str, Any]:
        """Returns a dictionary with the output of the ``STATUS`` command."""

        def check_int(s):
            if s[0] in ("-", "+"):
                return s[1:].isdigit()
            return s.isdigit()

        cmd = await self.send_command("STATUS", timeout=5)
        if not cmd.succeeded():
            error = cmd.status == ArchonCommandStatus.TIMEDOUT
            raise ArchonControllerError(
                f"Command STATUS finished with status {cmd.status.name!r}",
                set_error_status=error,
            )

        keywords = str(cmd.replies[0].reply).split()
        status = {
            key.lower(): int(value) if check_int(value) else float(value)
            for (key, value) in map(lambda k: k.split("="), keywords)
        }

        if update_power_bits:
            await self.power()

        return status

    async def get_frame(self) -> dict[str, int]:
        """Returns the frame information.

        All the returned values in the dictionary are integers in decimal
        representation.
        """

        cmd = await self.send_command("FRAME", timeout=5)
        if not cmd.succeeded():
            raise ArchonControllerError(
                f"Command FRAME failed with status {cmd.status.name!r}"
            )

        keywords = str(cmd.replies[0].reply).split()
        frame = {
            key.lower(): int(value) if "TIME" not in key else int(value, 16)
            for (key, value) in map(lambda k: k.split("="), keywords)
        }

        #print("get_frame: frame: %s" % str(frame))
        self.frame=frame
        return frame

    async def read_config(
        self,
        save: str | bool = False,
    ) -> tuple[configparser.ConfigParser, list[str]]:
        """Reads the configuration from the controller.

        Parameters
        ----------
        save
            Save the configuration to a file. If ``save=True``, the configuration will
            be saved to ``~/archon_<controller_name>.acf``, or set ``save`` to the path
            of the file to save.
        """

        key_value_re = re.compile("^(.+?)=(.*)$")

        def parse_line(line):
            match = key_value_re.match(line)
            assert match
            k, v = match.groups()
            # It seems the GUI replaces / with \ even if that doesn't seem
            # necessary in the INI format.
            k = k.replace("/", "\\")
            if ";" in v or "=" in v or "," in v:
                v = f'"{v}"'
            return k, v

        await self.send_command("POLLOFF")

        cmd_strs = [f"RCONFIG{n_line:04X}" for n_line in range(MAX_CONFIG_LINES)]
        done, failed = await self.send_many(cmd_strs, max_chunk=100, timeout=0.5)

        await self.send_command("POLLON")

        if len(failed) > 0:
            ff = failed[0]
            status = ff.status.name
            raise ArchonControllerError(
                f"An RCONFIG command returned with code {status!r}"
            )

        if any([len(cmd.replies) != 1 for cmd in done]):
            raise ArchonControllerError("Some commands did not get any reply.")

        lines = [str(cmd.replies[0]) for cmd in done]

        # Trim possible empty lines at the end.
        config_lines = "\n".join(lines).strip().splitlines()

        # The GUI ACF file includes the system information, so we get it.
        system = await self.get_system()

        c = configparser.ConfigParser()
        c.optionxform = str  # type: ignore  Make it case-sensitive
        c.add_section("SYSTEM")
        for sk, sv in system.items():
            if "_name" in sk.lower():
                continue
            sl = f"{sk.upper()}={sv}"
            k, v = parse_line(sl)
            c.set("SYSTEM", k, v)
        c.add_section("CONFIG")
        for cl in config_lines:
            k, v = parse_line(cl)
            c.set("CONFIG", k, v)

        if save is not False and save is not None:
            if isinstance(save, str):
                path = save
            else:
                path = os.path.expanduser(f"~/archon_{self.name}.acf")
            with open(path, "w") as f:
                c.write(f, space_around_delimiters=False)

        return (c, config_lines)

    async def hold_timing(self):
        cmd = await self.send_command("HOLDTIMING", timeout=1)
        if not cmd.succeeded():
          self.update_status(ControllerStatus.ERROR)
          raise ArchonControllerError(\
               f"Failed sending {cmd_str} ({cmd.status.name})")

    async def release_timing(self):
        cmd = await self.send_command("RELEASETIMING", timeout=1)
        if not cmd.succeeded():
          self.update_status(ControllerStatus.ERROR)
          raise ArchonControllerError(\
               f"Failed sending {cmd_str} ({cmd.status.name})")

    async def write_config(
        self,
        input: str | os.PathLike[str],
        applyall: bool = False,
        applymods: list[str] = [],
        poweron: bool = False,
        timeout: float | None = None,
        overrides: dict = {},
        #notifier: Optional[Callable[[str], None]] = None,
        release_timing: bool = True,
    ):
        """Writes a configuration file to the contoller.

        Parameters
        ----------
        input
            The path to the configuration file to load. It must be in INI format with
            a section called ``[CONFIG]``. It can also be a string containing the
            configuration itself.
        applyall
            Whether to run ``APPLYALL`` after successfully sending the configuration.
        applymods
            A list of apply commands to send to modules (e.g.,
            ``['LOADTIMING', 'APPLYMOD2']``).
        poweron
            Whether to run ``POWERON`` after successfully sending the configuration.
            Requires ``applyall=True``.
        timeout
            The amount of time to wait for each command to succeed.  If `None`, reads
            the value from the configuration entry for
            ``timeouts.write_config_timeout``.
        overrides
            A dictionary with configuration lines to be overridden. Must be a mapping
            of keywords to replace, including the module name (e.g.,
            ``MOD11/HEATERAP``), to the new values.
        #notifier
        #   A callback that receives a message with the current operation being
        #   performed. Useful when `.write_config` is called by the actor to report
        #   progress to the users.
        release_timing
            If True, allow controller to start its timing script after writing config file.
            If False, and "hold_timing()" was previously executed, then the controller will 
            not start the timing script until "release_timing()" is later
            executed. THis allow controllers connected by sync cables to synchronize their
            execution of their timing scripts.
        """

        ACS = ArchonCommandStatus

        #notifier = notifier or (lambda x: None)

        #notifier("Reading configuration file")

        timeout = timeout or self.config["timeouts"]["write_config_timeout"]
        delay: float = self.config["timeouts"]["write_config_delay"]

        cp = configparser.ConfigParser()

        input = str(input)
        if os.path.exists(input):
            cp.read(input)
        else:
            cp.read_string(input)

        if not cp.has_section("CONFIG"):
            raise ArchonControllerError(
                "The config file does not have a CONFIG section."
            )

        # Undo the INI format: revert \ to / and remove quotes around values.
        aconfig = cp["CONFIG"]
        lines = []
        for key in aconfig:
            lines.append(key.upper().replace("\\", "/") + "=" + aconfig[key].strip('"'))

        self.debug("Clearing previous configuration")
        await self.send_and_wait("CLEARCONFIG", timeout=timeout)

        self.debug("Sending configuration lines")

        # Stop the controller from polling internally to speed up network response
        # time. This command is not in the official documentation.
        await self.send_command("POLLOFF")

        cmd_strs = [f"WCONFIG{n_line:04X}{line}" for n_line, line in enumerate(lines)]
        for line in cmd_strs:
            cmd = await self.send_command(line, timeout=timeout)
            if cmd.status == ACS.FAILED or cmd.status == ACS.TIMEDOUT:
                self.update_status(ControllerStatus.ERROR)
                await self.send_command("POLLON")
                raise ArchonControllerError(
                    f"Failed sending line {cmd.raw!r} ({cmd.status.name})"
                )
            await asyncio.sleep(delay)

        self.acf_config = cp
        self.acf_file = input if os.path.exists(input) else None

        # Write overrides. Do not apply since we optionall do an APPLYALL afterwards.
        if overrides and len(overrides) > 0:
            self.debug("Writing configuration overrides.")
            for keyword, value in overrides.items():
                await self.write_line(keyword, value, apply=False)

        # Restore polling
        await self.send_command("POLLON")

        for mod in applymods:
            #notifier(f"Sending {mod.upper()}")
            await self.send_and_wait(mod.upper(), timeout=5)

        if applyall:
            #notifier("Sending APPLYALL")
            await self.send_and_wait("APPLYALL", timeout=5)

            # Reset objects that depend on the configuration file.
            self._parse_params()
            await self._set_default_window_params()

            if poweron:
                #notifier("Sending POWERON")
                await self.power(True)

        #notifier("resetting")
        await self.reset(release_timing=release_timing,sync_flag=False)

        return

    async def write_line(
        self,
        keyword: str,
        value: int | float | str,
        mod: Optional[str] = None,
        apply: bool | str = True,
    ):
        """Write a single line to the controller, replacing the current configuration.

        Parameters
        ----------
        keyword
            The config keyword to replace. If ``mod=None``, must include the module
            name (e.g., ``MOD11/HEATERAP``); otherwise the module is added from
            ``mod``. Modules and module keywords can be separated by slashes or
            backlashes.
        value
            The value of the keyword.
        mod
            The name of the keyword module, e.g., ``MOD11``.
        apply
            Whether to re-apply the configuration for the module. If ``apply``
            is a string, defines the command to be used to apply the new setting,
            e.g., ``APPLYCDS``.

        """

        if not self.acf_config:
            raise ArchonControllerError("The controller ACF configuration is unknown.")

        keyword = keyword.upper().replace("/", "\\")

        if mod != "" and mod is not None:
            mod = mod.upper()
            if not keyword.startswith(mod):
                keyword = mod + "\\" + keyword
        else:
            mod_re = re.match(r"(MOD[0-9]+)\\", keyword)
            if mod_re:
                mod = mod_re.group(1)

        current_keywords = [k.upper() for k in list(self.acf_config["CONFIG"])]

        if keyword not in current_keywords:
            raise ArchonControllerError(f"Invalid keyword {keyword}")

        n_line = current_keywords.index(keyword)

        if isinstance(value, (int, float)):
            value_str = str(value)
        elif isinstance(value, str):
            if any(quotable_char in value for quotable_char in [",", " ", "="]):
                value_str = '"' + value + '"'
            else:
                value_str = value

        # For WCONFIG we need to use MODX/KEYWORD.
        keyword_wconfig = keyword.replace("\\", "/")
        line = f"{keyword_wconfig}={value_str}"

        cmd = await self.send_command(f"WCONFIG{n_line:04X}{line}")
        if cmd.status == ArchonCommandStatus.FAILED:
            raise ArchonControllerError(
                f"Failed sending line {cmd.raw!r} ({cmd.status.name})"
            )

        self.acf_config["CONFIG"][keyword] = value_str

        if apply:
            if isinstance(apply, str):
                apply_cmd_str = apply.upper()
            else:
                if mod is None:
                    raise ArchonControllerError("Apply can only be used with modules.")
                modn = mod[3:]
                apply_cmd_str = f"APPLYMOD{modn}"

            cmd_apply = await self.send_command(apply_cmd_str)
            if cmd_apply.status == ArchonCommandStatus.FAILED:
                raise ArchonControllerError(f"Failed applying changes to {mod}.")

            self.debug(f"{keyword}={value_str}")

    async def power(self, mode: bool | None = None):
        """Handles power to the CCD(s). Sets the power status bit.

        Parameters
        ----------
        mode
            If `None`, returns `True` if the array is currently powered,
            `False` otherwise. If `True`, powers n the array; if `False`
            powers if off.

        Returns
        -------
        state : `.ArchonPower`
            The power state as an `.ArchonPower` flag.

        """

        if mode is not None:
            cmd_str = "POWERON" if mode is True else "POWEROFF"
            cmd = await self.send_command(cmd_str, timeout=10)
            if not cmd.succeeded():
                self.update_status([ControllerStatus.ERROR, ControllerStatus.POWERBAD])
                raise ArchonControllerError(
                    f"Failed sending POWERON ({cmd.status.name})"
                )

            await asyncio.sleep(1)

        status = await self.get_device_status(update_power_bits=False)

        power_status = ArchonPower(status["power"])

        if (
            power_status not in [ArchonPower.ON, ArchonPower.OFF]
            or status["powergood"] == 0
        ):
            if power_status == ArchonPower.INTERMEDIATE:
                warnings.warn("Power in INTERMEDIATE state.", ArchonUserWarning)
            self.update_status(ControllerStatus.POWERBAD)
        else:
            if power_status == ArchonPower.ON:
                self.update_status(ControllerStatus.POWERON)
            elif power_status == ArchonPower.OFF:
                self.update_status(ControllerStatus.POWEROFF)

        return power_status

    async def set_autoflush(self, mode: bool):
        """Enables or disables autoflushing."""

        self.debug("setting ContinuousExposures: %s" % mode)
        await self.set_param("ContinuousExposures", int(mode))

        self.auto_flush = mode

    async def reset(self, autoflush=True, release_timing=True, update_status=True, sync_flag=None):
        """Resets timing and discards current exposures."""

        if sync_flag is None:
           sync_flag = self.ls4_sync_io.sync_flag

        self._parse_params()

        self.debug(f"start resetting controller")

        self.debug(f"hold_timing")
        await self.hold_timing()

        self.debug(f"set autoflush %s" % autoflush)
        await self.set_autoflush(autoflush)
        self.debug(f"setting Exposures to 0")
        await self.set_param(param="Exposures", value=0, sync_flag=sync_flag)
        self.debug(f"setting ReadOut to 0")
        await self.set_param(param="ReadOut", value=0, sync_flag=sync_flag)
        self.debug(f"setting AbortExposure to 0")
        await self.set_param(param="AbortExposure", value=0, sync_flag=sync_flag)
        self.debug(f"setting DoFlush to 0")
        await self.set_param(param="DoFlush", value=0, sync_flag=sync_flag)
        self.debug(f"setting WaitCount to 0")
        await self.set_param(param="WaitCount", value=0, sync_flag=sync_flag)

        # Reset parameters to their default values.
        if "default_parameters" in self.config["archon"]:
            default_parameters = self.config["archon"]["default_parameters"]
            for param in default_parameters:
                self.debug(f"setting %s to %d" %\
                      (param, default_parameters[param]))
                await self.set_param(param=param, \
                      value=default_parameters[param], sync_flag=sync_flag)

        if release_timing:
            self.debug(f"release_timing .")
            await self.release_timing()

        if update_status:
            self._status = ControllerStatus.IDLE
            self.debug(f"awaiting self.power()")
            await self.power()  # Sets power bit.

        self.debug(f"done with reset")

    def _parse_params(self):
        """Reads the ACF file and constructs a dictionary of parameters."""

        if not self.acf_config:
            raise ArchonControllerError("ACF file not loaded. Cannot parse parameters.")

        # Dump the ACF ConfigParser object into a dummy file and read it as a string.
        f = io.StringIO()
        self.acf_config.write(f)

        f.seek(0)
        data = f.read()

        matches = re.findall(
            r'PARAMETER[0-9]+\s*=\s*"([A-Z]+)\s*=\s*([0-9]+)"',
            data,
            re.IGNORECASE,
        )

        self.parameters = {k.upper(): int(v) for k, v in dict(matches).items()}

    async def _set_default_window_params(self, reset: bool = True):
        """Sets the default window parameters.

        This is assumed to be called only after the default ACF has been loaded
        and before any calls to `.write_line` or `.set_param`. Resets the window.

        """

        self.default_window = {
            "lines": int(self.parameters.get("LINES", -1)),
            "pixels": int(self.parameters.get("PIXELS", -1)),
            "preskiplines": int(self.parameters.get("PRESKIPLINES", 0)),
            "postskiplines": int(self.parameters.get("POSTSKIPLINES", 0)),
            "preskippixels": int(self.parameters.get("PRESKIPPIXELS", 0)),
            "postskippixels": int(self.parameters.get("POSTSKIPPIXELS", 0)),
            "overscanpixels": int(self.parameters.get("OVERSCANPIXELS", 0)),
            "overscanlines": int(self.parameters.get("OVERSCANLINES", 0)),
            "hbin": int(self.parameters.get("HORIZONTALBINNING", 1)),
            "vbin": int(self.parameters.get("VERTICALBINNING", 1)),
        }

        #self.info(f"default window: {self.default_window}")

        self.current_window = self.default_window.copy()

        #self.info(f"current window: {self.current_window}")

        if reset:
            await self.reset_window()

    async def set_param(
        self,
        param: str,
        value: int,
        force: bool = False,
        sync_flag: bool | None = None
    ) -> ArchonCommand | None:

        """sets the parameter ``param`` to value ``value`` calling ``FASTLOADPARAM``.
           If self.ls4_sync_io.sync_flag is true, ls4_sync_io is used to synchronize
           execution of set_param across synchronized controllers

        """

        error_msg = None
        sync_test = False
        cmd = None
        prefix = self.prefix

        if sync_flag is None:
           sync_flag = self.ls4_sync_io.sync_flag

        if param in ["SYNCTEST","SYNC_TEST"]:
           sync_test = True

        self.debug("%s: setting [%s] to [%d] sync_flag: %s sync_test: %s" %\
           (prefix,param,value,sync_flag,sync_test))

        # First we check if the parameter actually exists.
        if len(self.parameters) == 0:
            if self.acf_config is None:
                raise ArchonControllerError("ACF not loaded. Cannot modify parameters.")

        param = param.upper()
          
        if (not sync_test) and (param not in self.parameters) and (force is False):
            error_msg = f"Trying to set unknown parameter {param}"

        if sync_flag and error_msg is None:
          # The leader breezes through sync_prepare without waiting for events.
          # The followers get held up in sync prepare until the leader executes sync_update (below)

          self.debug("%s preparing sync" % prefix)
          try:
            await self.ls4_sync_io.sync_prepare(param_args={'param':param,'value':value,'force':force},command_args=None)
          except Exception as e:
            error_msg = "Exception preparing sync: %s" % e

          # The leaders execute FASTPREPARM before the followers because it gets here first
          if not error_msg and not sync_test:

            self.debug("%s sending FASTPREPPARAM" % prefix)
            cmd = await self.send_command(f"FASTPREPPARAM {param} {value}",sync_flag=False)
            if not cmd.succeeded():
               error_msg = "%s failed preparing parameters %s to %s" % (prefix,param,value)

          # Here the leader allows the followers to catch up and send FASTPREPPARAM command
          if not error_msg:
            self.debug("%s updating sync" % prefix)
            try:
              await self.ls4_sync_io.sync_update(param_flag=True)
            except Exception as e:
              error_msg = "Exception updating sync: %s" % e

        # All the controller threads arrive here about the same time. However, if they
        # have been set up for synchronous IO, they will load the parameter at the same 
        # time. If they are not synchronized, the relative timing will be random.
        if not error_msg and not sync_test:
          cmd_string=f"FASTLOADPARAM {param} {value}"
          self.debug("%s sending command [%s]" % (prefix,cmd_string))
          try:
            #cmd = await self.send_command(f"FASTLOADPARAM {param} {value}")
            cmd = await self.send_command(cmd_string)
            if not cmd.succeeded():
               error_msg = f"Failed sending command [%s]" % cmd_string
          except Exception as e:
            error_msg = "Exception setting param: %s" % e

        # synchronization house-keeping
        if not error_msg and sync_flag:
          try:
            self.debug("%s verifying sync" % prefix)
            await self.ls4_sync_io.sync_verify(param_flag=True)
          except Exception as e:
            error_msg = "Exception verifying sync: %s" % e

        if error_msg is not None:
           self.error("%s: %s" % (prefix,error_msg))
           raise ArchonControllerError(f"Failed setting param {param} to value {value}:  %s" % error_msg)

        self.parameters[param] = value
        self.debug("%s: done setting [%s] to [%d] sync_flag: %s sync_test: %s" %\
           (prefix,param,value,sync_flag,sync_test))
        
        return cmd

    async def reset_window(self):
        """Resets the exposure window."""

        await self.set_window(**self.default_window)

    async def set_window(
        self,
        lines: int | None = None,
        pixels: int | None = None,
        preskiplines: int | None = None,
        postskiplines: int | None = None,
        preskippixels: int | None = None,
        postskippixels: int | None = None,
        overscanlines: int | None = None,
        overscanpixels: int | None = None,
        hbin: int | None = None,
        vbin: int | None = None,
    ):
        """Sets the CCD window."""

        if lines is None:
            lines = self.current_window["lines"]

        if pixels is None:
            pixels = self.current_window["pixels"]

        if preskiplines is None:
            preskiplines = self.current_window["preskiplines"]

        if postskiplines is None:
            postskiplines = self.current_window["postskiplines"]

        if preskippixels is None:
            preskippixels = self.current_window["preskippixels"]

        if postskippixels is None:
            postskippixels = self.current_window["postskippixels"]

        if overscanlines is None:
            overscanlines = self.current_window["overscanlines"]

        if overscanpixels is None:
            overscanpixels = self.current_window["overscanpixels"]

        if vbin is None:
            vbin = self.current_window["vbin"]

        if hbin is None:
            hbin = self.current_window["hbin"]

        if lines >= 0:
            await self.set_param("Lines", lines)
        else:
            warnings.warn("Lines value unknown. Did not set.", ArchonUserWarning)

        if pixels >= 0:
            await self.set_param("Pixels", pixels)
        else:
            warnings.warn("Pixels value unknown. Did not set.", ArchonUserWarning)

        await self.set_param("Pixels", pixels)
        await self.set_param("PreSkipLines", preskiplines)
        await self.set_param("PostSkipLines", postskiplines)
        await self.set_param("PreSkipPixels", preskippixels)
        await self.set_param("PostSkipPixels", postskippixels)
        await self.set_param("VerticalBinning", vbin)
        await self.set_param("HorizontalBinning", hbin)

        linecount = (lines + overscanlines) // vbin
        pixelcount = (pixels + overscanpixels) // hbin

        await self.write_line("LINECOUNT", linecount, apply=False)
        await self.write_line("PIXELCOUNT", pixelcount, apply="APPLYCDS")

        self.current_window = {
            "lines": lines,
            "pixels": pixels,
            "preskiplines": preskiplines,
            "postskiplines": postskiplines,
            "preskippixels": preskippixels,
            "postskippixels": postskippixels,
            "overscanpixels": overscanpixels,
            "overscanlines": overscanlines,
            "hbin": hbin,
            "vbin": vbin,
        }

        #self.info(f"current window: {self.current_window}")

        return self.current_window


    async def expose(
        self,
        exposure_time: float = 1,
        readout: bool = True,
    ) -> asyncio.Task:
        """Integrates the CCD for ``exposure_time`` seconds.

        Returns immediately once the exposure has begun. If ``readout=False``, does
        not trigger a readout immediately after the integration finishes. The returned
        `~asyncio.Task` waits until the integration is done and, if ``readout``, checks
        that the readout has started.
        """

        #self.notifier(f"%s: preparing for exposure duration exposure {exposure_time} " % self.get_obsdate())

        CS = ControllerStatus

        if not (CS.IDLE & self.status):
            raise ArchonControllerError("The controller is not idle.")

        if CS.READOUT_PENDING & self.status:
            raise ArchonControllerError(
                "Controller has a readout pending. Read the device or flush."
            )

        if (not (CS.POWERON & self.status)) or (CS.POWERBAD & self.status):
            raise ArchonControllerError("Controller power is off or invalid.")

        #await self.reset(autoflush=False, release_timing=False,sync_flag=self.ls4_sync_io.sync_flag)
        await self.reset(autoflush=False, release_timing=False,sync_flag=False)
        #self.info(f"%s: done resetting",self.get_obsdate()) 
        if self.ls4_sync_io.sync_flag:
           self.debug(f"syncing up")
           await self.set_param(param="SYNCTEST",value=0)

        # Set integration time in centiseconds (yep, centiseconds).
        self.debug(f"setting IntCS to %d" % int(exposure_time * 100))
        await self.set_param("IntCS", int(exposure_time * 100))

        if readout is False:
            self.debug(f"skipping readout: setting Readout param to 0")
            await self.set_param("ReadOut", 0)
        else:
            self.debug(f"reading out: setting Readout param to 1")
            await self.set_param("ReadOut", 1)

        self.debug(f"setting Exposures to 1")
        await self.set_param("Exposures", 1)

        self.config['expose params']['exptime']=0.0
        self.config['expose params']['read-per']=0.0

        self.debug(f"sending RELEASETIMING")
        await self.send_command("RELEASETIMING")
        self.debug(f"updating status to EXPOSING and READOUT_PENDING")
        self.update_status([CS.EXPOSING, CS.READOUT_PENDING])
        self.timing['expose'].start()
        tm = time.gmtime()
        self.config['expose params']['dateobs']=self.get_obsdate(tm)
        self.config['expose params']['startobs']=self.get_obsdate(tm)

        #self.notifier(f"%s: starting exposure of duration exposure {exposure_time} " % self.get_obsdate())
        async def update_state():
           dt = 0.0
           done=True
           aborted=False
           t_start=time.time()
           if exposure_time>0.0 and dt < exposure_time:
              #self.notifier(f"%s: waiting %7.3f sec for exposure to end" %\
              #    (self.get_obsdate(),exposure_time))
              done = False
              aborted = False
              while (not done) and (not aborted):
                 if dt >= exposure_time:
                    #self.notifier(f"update_state: end %s:  exposure completed after %7.3f sec" % (self.get_obsdate(tm),dt))
                    done= True
                 elif not (self.status & CS.EXPOSING):  # Must have been aborted.
                    self.notifier(f"update_state: exposure was aborted after %7.3f sec" % dt)
                    aborted=True
                 else:
                    await asyncio.sleep(0.01)
                    dt = time.time()-t_start
                    tm = time.gmtime()
           else:
              self.debug(f"update_state: skipping 0-sec exposure loop")

           self.timing['expose'].end()
           self.config['expose params']['exptime']=self.timing['expose'].period
           self.config['expose params']['doneobs']=self.get_obsdate(tm)
           self.update_status(CS.EXPOSING, 'off')
           #self.notifier(f"%s: done with exposure of duration exposure {exposure_time} " % self.get_obsdate())
            
           if done:
              if aborted:
                 pass
              elif not readout: # readout later
                 self.debug(f"update_state: updating status to IDLE, READOUT_PENDING")
                 self.update_status(CS.READOUT_PENDING)
                 #self.update_status([CS.IDLE, CS.READOUT_PENDING])
              else: # readout now
                 #self.notifier(f"update_state: starting readout")
                 frame = await self.get_frame()
                 wbuf = frame["wbuf"]
                 if frame[f"buf{wbuf}complete"] == 0:
                    self.update_status(
                      [CS.EXPOSING, CS.READOUT_PENDING],
                      "off",
                      notify=False,
                    )
                    self.update_status(CS.READING)
                    self.timing['readout'].start()
                 else:
                    self.notifier(f"update_state: failed starting readout")
                    raise ArchonControllerError("Controller is not reading.")

           if not readout:
              self.timing['readout'].end()
              self.config['expose params']['read-per']=self.timing['readout'].period


        self.debug(f"%s: returning awaited update_state function" % self.get_obsdate(time.gmtime()))
        return await update_state()
        #return 

    async def abort(self, readout: bool = False):
        """Aborts the current exposure.

        If ``readout=False``, does not trigger a readout immediately after aborting.
        Aborting does not flush the charge.
        """

        if self.notifier:
          self.notifier("aborting controller.")

        CS = ControllerStatus

        if not self.status & ControllerStatus.EXPOSING:
            raise ArchonControllerError("Controller is not exposing.")

        await self.set_param("ReadOut", int(readout))
        await self.set_param("AbortExposure", 1)

        if readout:
            self.update_status([CS.EXPOSING, CS.READOUT_PENDING], "off", notify=False)
            self.update_status(CS.READING)
        else:
            self.update_status([CS.IDLE, CS.READOUT_PENDING])

        return

    async def flush(self, count: int = 2, wait_for: Optional[float] = None):
        """Resets and flushes the detector. Blocks until flushing completes."""

        if self.notifier: 
          self.notifier("flushing.")

        await self.reset(release_timing=False,sync_flag=False)

        await self.set_param("FlushCount", int(count))
        await self.set_param("DoFlush", 1)
        await self.send_command("RELEASETIMING")

        self.update_status(ControllerStatus.FLUSHING)

        wait_for = wait_for or self.config["timeouts"]["flushing"]
        assert wait_for

        await asyncio.sleep(wait_for * count)

        self.update_status(ControllerStatus.IDLE)

    async def readout(
        self,
        force: bool = False,
        block: bool = True,
        #delay: int = 0,
        wait_for: float | None = None,
        #notifier: Optional[Callable[[str], None]] = None,
        idle_after: bool = True,
    ):
        """Reads the detector into a buffer.

        If ``force``, triggers the readout routine regardless of the detector expected
        state. If ``block``, blocks until the buffer has been fully written. Otherwise
        returns immediately. 

        # not implemented in LS4 timing code
        A ``delay`` can be passed to slow down the readout by as
        many seconds (useful for creating photon transfer frames).
        """

        #if notifier:
        #  notifier(f"synchronizing...")

        await self.set_param(param="SYNCTEST",value=0)

        #if notifier:
        #  notifier(f"start reading out controller.")

        if not force and not (
            (self.status & ControllerStatus.READOUT_PENDING)
            and (self.status & ControllerStatus.IDLE)
        ):
            raise ArchonControllerError(f"Controller is not in a readable state.")

        """
        delay = int(delay)

        if delay > 0:
           #if notifier:
           #    notifier(f"setting WaitCount to {delay}")
           await self.set_param("WaitCount", delay)
        """

        #if notifier:
        #   notifier (f"reset...")

        await self.reset(autoflush=False, release_timing=False, update_status=False,sync_flag=False)

        #if notifier:
        #  notifier(f"set Readout to 1")

        await self.set_param("ReadOut", 1)

        #if notifier:
        #   notifier(f"sending READLEASETIMING")

        await self.send_command("RELEASETIMING")

        self.timing['readout'].start()
        #if notifier:
        #   notifier (f"update_status READING")

        self.update_status(ControllerStatus.READING, notify=False)

        #if notifier:
        #   notifier(f"update_status READOUT_PENDING")

        self.update_status(ControllerStatus.READOUT_PENDING, "off")

        if not block:
           #if notifier:
           #   notifier(f"not block, returning")
           return

        #max_wait = self.config["timeouts"]["readout_max"] + delay
        max_wait = self.config["timeouts"]["readout_max"] 

        wait_for = wait_for or 3  # sec delay to ensure the new frame starts filling.
        #if notifier:
        #  notifier(f"sleeping {wait_for} sec to make sure readout has started")

        await asyncio.sleep(wait_for)
        waited = wait_for

        frame = await self.get_frame()
        wbuf = frame["wbuf"]

        #if notifier:
        #   notifier(f"Reading frame to buffer {wbuf}.")

        dt = 0.0
        status_interval = 1.0
        update_interval = 0.01
        #update_interval = 1.0

        done = False
        timeout = False
        lines_read_prev = -1
        while (not done) and (not timeout):
           if waited > max_wait:
              timeout = True
           else:
              frame = await self.get_frame()
              if frame[f"buf{wbuf}complete"] == 1:
                 done=True
           if not done:
              if self.notifier and dt > status_interval:
                 dt = 0.0
                 pixels_read=frame[f"buf{wbuf}pixels"]
                 lines_read=frame[f"buf{wbuf}lines"]
                 w= int(waited)
                 if self.notifier:
                   self.notifier(f"{w}: frame is not complete: {pixels_read} pixel {lines_read} lines")
                 if lines_read <= lines_read_prev:
                    if self.notifier:
                      self.notifier("ERROR reading out at lines_read = %d" % lines_read)
                    timeout=True
                 else:
                    lines_read_prev = lines_read
              await asyncio.sleep(update_interval)
              dt += update_interval
              waited += update_interval

        self.timing['readout'].end()
        self.config['expose params']['read-per']=self.timing['readout'].period

        if done:
           if self.notifier:
               self.notifier(f"done reading out controller in %7.3f sec" % self.timing['readout'].period)
           if idle_after:
               #notifier(f"idling controller...")
               self.update_status(ControllerStatus.IDLE)
               #notifier(f"done idling controller...")
           # Reset autoflushing.
           await self.set_autoflush(True)

        elif timeout:
           if self.notifier:
               self.notifier(f"timeout reading out controller")
           self.update_status(ControllerStatus.ERROR)
           raise ArchonControllerError(\
                f"{self.name}:Timed out waiting for controller to finish reading.")

        return wbuf

    @overload
    async def fetch(
        self,
        buffer_no: int = -1,
        #notifier: Optional[Callable[[str], None]] = None,
        *,
        return_buffer: Literal[False],
    ) -> numpy.ndarray:
        ...

    @overload
    async def fetch(
        self,
        buffer_no: int = -1,
        #notifier: Optional[Callable[[str], None]] = None,
        *,
        return_buffer: Literal[True],
    ) -> tuple[numpy.ndarray, int]:
        ...

    @overload
    async def fetch(
        self,
        buffer_no: int = -1,
        #notifier: Optional[Callable[[str], None]] = None,
        return_buffer: bool = False,
    ) -> numpy.ndarray:
        ...

    async def fetch(
        self,
        buffer_no: int = -1,
        #notifier: Optional[Callable[[str], None]] = None,
        return_buffer: bool = False,
    ):
        """Fetches a frame buffer and returns a Numpy array.

        Parameters
        ----------
        buffer_no
            The frame buffer number to read. Use ``-1`` to read the most recently
            complete frame.
        return_buffer
            If `True`, returns the buffer number returned.

        Returns
        -------
        data
            If ``return_buffer=False``, returns the fetched data as a Numpy array.
            If ``return_buffer=True`` returns a tuple with the Numpy array and
            the buffer number.

        """

        self.timing['fetch'].start()

        if self.notifier:
          self.notifier("start fetching data from buffer %d" % buffer_no)

        if self.status & ControllerStatus.FETCHING:
            raise ArchonControllerError("Controller is already fetching")

        frame_info = await self.get_frame()

        if buffer_no not in [1, 2, 3, -1]:
            raise ArchonControllerError(f"Invalid frame buffer {buffer_no}")

        if buffer_no == -1:
            buffers = [
                (n, frame_info[f"buf{n}timestamp"])
                for n in [1, 2, 3]
                if frame_info[f"buf{n}complete"] == 1
            ]
            if len(buffers) == 0:
                raise ArchonControllerError("There are no buffers ready to be read")
            sorted_buffers = sorted(buffers, key=lambda x: x[1], reverse=True)
            buffer_no = sorted_buffers[0][0]
        else:
            if frame_info[f"buf{buffer_no}complete"] == 0:
                raise ArchonControllerError(f"Buffer frame {buffer_no} cannot be read")

        self.update_status(ControllerStatus.FETCHING)

        # Lock for reading
        await self.send_command(f"LOCK{buffer_no}",sync_flag=False)

        width = frame_info[f"buf{buffer_no}width"]
        height = frame_info[f"buf{buffer_no}height"]
        bytes_per_pixel = 2 if frame_info[f"buf{buffer_no}sample"] == 0 else 4
        n_bytes = width * height * bytes_per_pixel
        n_blocks: int = int(numpy.ceil(n_bytes / 1024.0))

        start_address = frame_info[f"buf{buffer_no}base"]

        # Set the expected length of binary buffer to read, including the prefixes.
        self.set_binary_reply_size((1024 + 4) * n_blocks)

        cmd_string = f"FETCH{start_address:08X}{n_blocks:08X}"
        #if self.notifier:
        #  self.notifier ("sending command [%s] with timout=None and sync_flag=False" % cmd_string)
        #cmd: ArchonCommand = await self.send_command(
        #   f"FETCH{start_address:08X}{n_blocks:08X}",
        #   timeout=None,sync_flag=False
        #
        cmd: ArchonCommand = await self.send_command(
            cmd_string, timeout=None,sync_flag=False
        )
        #if self.notifier:
        #  self.notifier ("done sending command [%s] with timout=None and sync_flag=False" % cmd_string)

        # Unlock all
        await self.send_command("LOCK0",sync_flag=False)

        # The full read buffer probably contains some extra bytes to complete the 1024
        # reply. We get only the bytes we know are part of the buffer.
        frame = cast(bytes, cmd.replies[0].reply[0:n_bytes])

        # Convert to uint16 array and reshape.
        dtype = f"<u{bytes_per_pixel}"  # Buffer is little-endian
        arr = numpy.frombuffer(frame, dtype=dtype)
        arr = arr.reshape(height, width)

        # Turn off FETCHING bit
        #self.update_status(ControllerStatus.IDLE)
        self.update_status(ControllerStatus.FETCHING, mode = 'off')

        self.timing['fetch'].end()
        if self.notifier:
          self.notifier("done fetching data in %7.3f sec" % self.timing['fetch'].period)

        if return_buffer:
            return (arr, buffer_no)

        return arr

    def set_binary_reply_size(self, size: int):
        """Sets the size of the binary buffers."""

        self._binary_reply = bytearray(size)

    async def _listen(self):
        """Listens to the reader stream and callbacks on message received."""

        if not self._client:  # pragma: no cover
            raise RuntimeError("Connection is not open.")

        assert self._client and self._client.reader

        n_binary = 0
        while True:
            # Max length of a reply is 1024 bytes for the message preceded by <xx:
            # We read the first four characters (the maximum length of a complete
            # message: ?xx\n or <xx\n). If the message ends in a newline, we are done;
            # if the message ends with ":", it means what follows are 1024 binary
            # characters without a newline; otherwise, read until the newline which
            # marks the end of this message. In binary, if the response is < 1024
            # bytes, the remaining bytes are filled with NULL (0x00).
            try:
                line = await self._client.reader.readexactly(4)
            except asyncio.IncompleteReadError:
                return

            if line[-1] == ord(b"\n"):
                pass
            elif line[-1] == ord(b":"):
                line += await self._client.reader.readexactly(1024)
                # If we know the length of the binary reply to expect, we set that
                # slice of the bytearray and continue. We wait until all the buffer
                # has been read before sending the notification. This is significantly
                # more efficient because we don't create an ArchonCommandReply for each
                # chunk of the binary reply. It is, however, necessary to know the
                # exact size of the reply because there is nothing that we can parse
                # to know a reply is the last one. Also, we don't want to keep appending
                # to a bytes string. We need to allocate all the memory first with
                # a bytearray or it's very inefficient.
                #
                # NOTE: this assumes that once the binary reply begins, no other
                # reply is going to arrive in the middle of it. I think that's unlikely,
                # and probably prevented by the controller, but it's worth keeping in
                # mind.
                #
                if self._binary_reply:
                    self._binary_reply[n_binary : n_binary + 1028] = line
                    n_binary += 1028  # How many bytes of the binary reply have we read.
                    if n_binary == len(self._binary_reply):
                        # This was the last chunk. Set line to the full reply and
                        # reset the binary reply and counter.
                        line = self._binary_reply
                        self._binary_reply = None
                        n_binary = 0
                    else:
                        # Skip notifying because the binary reply is still incomplete.
                        continue
            else:
                line += await self._client.reader.readuntil(b"\n")

            self.notify(line)

    def _get_id(self) -> int:
        """Returns an identifier from the pool."""

        if len(self._id_pool) == 0:
            raise ArchonControllerError("No ids remaining in the pool!")

        return self._id_pool.pop()

    async def __track_commands(self):
        """Removes complete commands from the list of running commands."""

        while True:
            done_cids = []
            for cid in self.__running_commands.keys():
                if self.__running_commands[cid].done():
                    self._id_pool.add(cid)
                    done_cids.append(cid)
            for cid in done_cids:
                self.__running_commands.pop(cid)
            await asyncio.sleep(0.5)


    def _get_id(self) -> int:
        """Returns an identifier from the pool."""

        if len(self._id_pool) == 0:
            self._id_pool = set(range(MAX_COMMAND_ID))
            #raise ArchonControllerError("No ids remaining in the pool!")

        return self._id_pool.pop()

    async def erase(self):
        """Run the LBNL erase procedure."""
 
        if self.notifier:
          self.notifier("erasing.")

        await self.reset(release_timing=False, autoflush=False,sync_flag=False)

        self.update_status(ControllerStatus.FLUSHING)

        """
        await self.set_param("DoErase", 1)
        await self.send_command("RELEASETIMING")
        """
        await asyncio.sleep(2)  # Real time should be ~0.6 seconds.

        self.update_status(ControllerStatus.IDLE)
        #self.update_status(ControllerStatus.FLUSHING,mode='off')
        #await self.reset(sync_flag=False)
        # DEBUG
        #await self.reset(autoflush=False, sync_flag=False)

    async def cleanup(
        self,
        erase: bool = False,
        n_cycles: int = 10,
        fast: bool = False,
        #notifier: Callable[[str], None] | None = None,
    ):
        """Runs a cleanup procedure for the LBNL chip.

        Executes a number of cycles of the e-purge routine followed by a chip
        flush (complete or fast). After the e-purge cycles have been completed,
        runs three full flushing cycles.

        Parameters
        ----------
        erase
            Calls the `.erase` routine before running the e-purge cycle.
        n_cycles
            Number of e-purge/flushing cycles to execute.
        fast
            If `False`, a complete flushing is executed after each e-purge (each
            line is shifted and read). If `True`, a binning factor of 10 is used.
        #notifier
        #    A function to call to output messages (usually a command write method).

        """

        #if notifier is None:
        #    notifier = lambda text: None  # noqa

        if erase:
            #notifier("Erasing chip.")
            await self.erase()

        mode = "fast" if fast else "normal"
        purge_msg = f"Doing {n_cycles} with DoPurge=1 (mode={mode})"
        if self.notifier:
          self.notifier(purge_msg)

        for ii in range(n_cycles):
            #notifier(f"Cycle {ii+1} of {n_cycles}.")
            await self.purge(fast=fast)

        await self.set_param("DoPurge", 0)

        #flush_msg = "Flushing 3x"
        if self.notifier:
          self.notifier(flush_msg)

        await self.flush(3)

        await self.reset(sync_flag=False)

        return True

    async def purge(self, fast: bool = True):
        """Runs a single cycle of the e-purge routine.

        A cycle consists of an execution of the e-purge routine followed by a
        chip flushing.

        Parameters
        ----------
        fast
            If `False`, a complete flushing is executed after the e-purge (each
            line is shifted and read). If `True`, a binning factor of 10 is used.

        """

        if self.notifier:
          self.notifier("Running e-purge.")

        if fast:
            await self.set_param("FLUSHBIN", 10)
            await self.set_param("SKIPLINEBINVSHIFT", 220)
        else:
            await self.set_param("FLUSHBIN", 2200)
            await self.set_param("SKIPLINEBINVSHIFT", 1)

        await self.reset(release_timing=False,sync_flag=False)

        self.update_status(ControllerStatus.FLUSHING)

        await self.set_param("DOPURGE", 1)
        await self.send_command("RELEASETIMING")

        #self.info("self.config = %s" % self.config)
        #
        flush_time = self.config["timeouts"]["flushing"]
        if fast:
            flush_time = self.config["timeouts"]["fast_flushing"]

        await asyncio.sleep(self.config["timeouts"]["purge"] + flush_time)

        await self.set_param("FLUSHBIN", 2200)
        await self.set_param("SKIPLINEBINVSHIFT", 1)

        await self.reset(sync_flag=False)

        return True

if "__name__" == "__main__":

    print("hello")
