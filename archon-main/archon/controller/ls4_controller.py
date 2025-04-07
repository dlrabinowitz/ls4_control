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
from archon.controller.ls4_mainloop import Mainloop_Function as ML
from archon.controller.ls4_mainloop import LS4_Mainloop
from archon.controller.ls4_fake_controller import LS4_Fake_Control
from archon.ls4_exceptions import (
    LS4ControllerError,
    LS4ControllerWarning,
    LS4UserWarning,
)
from archon.tools import get_obsdate

from archon.controller.ls4_params import\
              MAX_COMMAND_ID, MAX_CONFIG_LINES, FOLLOWER_TIMEOUT_MSEC, \
              P100_SUPPLY_VOLTAGE, N100_SUPPLY_VOLTAGE, AMPS_PER_CCD, \
              CCDS_PER_QUAD, STATUS_LOCK_TIMEOUT, LS4_BLOCK_SIZE, \
              VSUB_ENABLE_KEYWORD, VSUB_MODULE, VSUB_ENABLE_VAL, \
              VSUB_DISABLE_VAL, VSUB_APPLY_COMMAND, MAX_FETCH_TIME, \
              STATUS_START_BIT,REBOOT_TIME, POST_ERASE_DELAY


__all__ = ["LS4Controller", "TimePeriod"]

def check_int(s):
    if s[0] in ("-", "+"):
        return s[1:].isdigit()
    return s.isdigit()

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

    param_args: a list of dictionaries, one for each controller, to record "set_param" arguments

    command_args: a list of dictionaries, one for each controller, to record "send_commnd" arguments

    ls4_events: an instance of LS4_Events, which has functions to synchronous controller operations

    ls4_logger: an instance of LS4_Logger, for logging diagnostic messages

    idle_function: the name of the camera operation to be run while idle (see ls4_mainloop.Mainloop_Function)

    fake: If true, controllers are faked (they need not be connected or power up)

    timing: a dictionary to record times taken to  expose, readout, and fetch

    reboot: If true, reboot the controllers before configuraing

    notifier: function to call when logging messages (redundant with ls4_logger)
    """

    # auto_functions are the possible operations performed by the controller timing
    # code on each pass through its main loop. 

    
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
        idle_function: ML | None = None,
        fake: bool | None = None,
        timing = None,
        acf_file: str | None = None,
        reboot: bool | None = None,
        notifier: Optional[Callable[[str], None]] = None,
    ):

        assert param_args is not None, "param_args are not specified"
        assert command_args is not None, "command_args are not specified"
        assert ls4_events is not None, "ls4_events are not specified"

        self.notifier_callback = notifier

        if reboot is None:
           self.reboot = False
        else:
           self.reboot = True

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

        self.fake_controller = False

        self._status: ControllerStatus = ControllerStatus.UNKNOWN
        self.__status_event = asyncio.Event()
        
        self.debug("instantiating state_lock")
        # need a mutex to lock self._status while changing status bits
        self.status_lock = threading.Lock()
        self.debug("done instantiating state_lock")

        self.host = host
        self.name = name

        self._binary_reply: Optional[bytearray] = None


        self.parameters: dict[str, int] = {}

        self.current_window: dict[str, int] = {}
        self.default_window: dict[str, int] = {}

        self.config = config or lib_config
        self.debug("self.config = %s" % str(self.config))

        self.acf_config: configparser.ConfigParser | None = None

        self.acf_file = acf_file

        # self.fake_control will be used to simulate controller operations
        self.fake_control = None
        if fake is not None:
           self.fake_controller = fake
 
        if self.fake_controller:
           try:
             self.debug("instantiating LS4_Fake_Control")
             self.fake_control = LS4_Fake_Control(ls4_logger=self.ls4_logger)
             self.debug("done instantiating LS4_Fake_Control")
           except Exception as e:
             error_msg = "Exception instantiating LS4_Fake_Control: %s" % e
             raise LS4ControllerError(error_msg)


        #self.add_logger(info=info, error=error, debug=debug, warn = warn)

        self.info("\n\tname: %s    host: %s    port: %d    local_addr: %s    fake: %s" %\
             (name,host,port,local_addr,fake))

        if reboot:
           self.info("rebooting controller")
           if not self.fake_controller:
             #command_string = "echo " + "'" + ">01REBOOT" + "'" + " | netcat -N %s %s" % (host,port)
             command_string = "echo " + "'" + ">01REBOOT" + "'" + " | netcat %s %s\n" % (host,port)
             self.info("command_string is %s" % command_string)
             os.system(command_string)
             #self.debug("sleeping %7.3f sec" % REBOOT_TIME)
             #time.sleep(REBOOT_TIME)
           self.info("done rebooting controller")

             
        self.__running_commands: dict[int, ArchonCommand] = {}
        self._id_pool = set(range(MAX_COMMAND_ID))
        LS4_Device.__init__(self, name=name, host=host, port=port, local_addr=local_addr,
                    ls4_logger=self.ls4_logger,config=self.config)

        # TODO: asyncio recommends using asyncio.create_task directly, but that
        # call get_running_loop() which fails in iPython.
        self._job = asyncio.get_event_loop().create_task(self.__track_commands())

        self.frame=None
      
        if "timeouts" not in self.config:
            self.config["timeouts"]={}

        self.config["timeouts"].update(\
            {"write_config_timeout": 2,\
            "write_config_delay": 0.0001,\
            "expose_timeout": 2,\
            "readout_max": 30,\
            "flush": 60.0,\
            "fast_flush": 6.0,\
            "purge": 60.0,\
            "erase": 60.0})

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
             
        if "expose_params" not in self.config:
            self.config["expose_params"]={}

        self.config["expose_params"].update(\
               {"date-obs":"0000-00-00T00:00:00",\
                "object": "TEST",\
                "obsmode": "TEST",\
                "imagetyp": "TEST",\
                "actexpt": 0.0,\
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
        self.default_idle_function = idle_function
        self.mainloop = LS4_Mainloop(ls4_controller=self,ls4_logger=self.ls4_logger, 
                        default_function = idle_function)

    def notifier(self,str):
        if self.notifier_callback is not None:
           self.notifier_callback(str)
        else:
           pass

    def set_lead(self, lead_flag: bool = False):
         self.leader = lead_flag
         self.prefix = "leader %s" % self.name
         if self.ls4_sync_io is not None:
            self.ls4_sync_io.set_lead(lead_flag)

    async def start(self, reset: bool = True, read_acf: bool = True):
        """
           Starts the controller connection. 
           If ``reset=True``, resets the status.
        """

        self.info(f"testing connection to controller {self.name}")
        error_msg = None
        try:
           if self.fake_controller:
              alive=True
           else:
              alive = await super().test_connection()
           if not alive:
               error_msg = f"controller {self.name} is not accepting connections"
           else:
               self.info(f"controller {self.name} is allowing connections")
        except Exception as e:
           error_msg = f"exception testing connection to controller {self.name}: %s" % e

        assert error_msg is None , error_msg

        if not self.fake_controller:
          await super().start()
        self.debug(f"Controller {self.name} connected at {self.host}.")

        if read_acf :
            if self.fake_controller and self.acf_file is None:
              error_msg = "cannot retrieve XVS data from acf_file. acf_file is None"
              self.error(error_msg)
              raise LS4ControllerError(error_msg)
              
            elif self.fake_controller:
              self.debug(f"Retrieving ACF data from acf_file {self.acf_file}.")
              try:
                 self.acf_config = self.acf_file_to_parser(acf_file=self.acf_file)
              except Exception as e:
                 error_msg = "exception getting acf_config: %s" %e 
                 self.error(error_msg)
                 raise LS4ControllerError(error_msg)
              self.debug(f"Done retrieving ACF data from acf_file {self.acf_file}.")

            else:
              self.debug(f"Retrieving ACF data from controller {self.name}.")
              config_parser, _ = await self.read_config()
              self.acf_config = config_parser
              self._parse_params()

        # disable shutter on power up
        self.shutter_enable=False


        if reset:
            try:
                await self._set_default_window_params()
                await self.reset(sync_flag=False,idle_function=self.default_idle_function)
            except LS4ControllerError as err:
                warnings.warn(f"Failed resetting controller: {err}", LS4UserWarning)

        return self

    def acf_file_to_parser(self,acf_file=None):

        cp = None
        if acf_file is not None:
          cp = configparser.ConfigParser()

          input = str(acf_file)
          if os.path.exists(input):
             cp.read(input)
          else:
             self.warn("acf_file [%s] does not exist" % acf_file)
        else:
             self.warn("acf_file is not specified")

        return cp


    @property
    def status(self) -> ControllerStatus:
        """Returns the status of the controller as a `.ControllerStatus` enum type."""

        try:
          if not self.status_lock.acquire(timeout=STATUS_LOCK_TIMEOUT):
             error_msg = "ERROR: failed to acquire status lock within %7.3f sec" %\
                  STATUS_LOCK_TIMEOUT
             self.warn(error_msg)
        except Exception as e:
          error_msg = "Exception acquiring status lock: %s" % e
          self.warn(error_msg)

        state = self._status
        try:
          self.status_lock.release()
        except Exception as e:
          error_msg = "Exception releasing status lock"
          self.warn(error_msg)

        return state

    @property
    def status_bits(self):
        """ return dictionary with value of each named status bit """
        return self.status.status_dict

    async def is_idle(self):
        return await self.check_status(ControllerStatus.IDLE)

    async def is_exposing(self):
        return await self.check_status(ControllerStatus.EXPOSING)

    async def is_readout_pending(self):
        return await self.check_status(ControllerStatus.READOUT_PENDING)

    async def is_reading(self):
        return await self.check_status(ControllerStatus.READING)

    async def is_fetching(self):
        return await self.check_status(ControllerStatus.FETCHING)

    async def is_fetch_pending(self):
        return await self.check_status(ControllerStatus.FETCH_PENDING)

    async def is_power_on(self):
        return await self.check_status(ControllerStatus.POWERON)

    async def is_power_bad(self):
        return await self.check_status(ControllerStatus.POWERBAD)

    async def check_status(
        self,
        bits: ControllerStatus | list[ControllerStatus],
        mode="or",
        wait_flag = False,
        max_wait_time = 0.0,
    ):

        """ check if any, none, or all (mode='or', 'nor', or 'and')
            of the specified status bits are set

            if wait_flag is True, wait up to max_wait_time sec for the
            status bits to change to the required value.

        """

        assert mode in ['or','nor','and'], \
          "mode must be in [or, nor, and]"

        if not isinstance(bits, (list, tuple)):
            bits = [bits]
         
        result = False

        # create as mask with only the specifed bits set to 1
        mask = ControllerStatus.NOSTATUS
        for b in bits:
           mask |= b
  
        if wait_flag:

          # yield_status is a generator that returns the controller
          # status every time the status bits change. When the
          # returned status value matches the specified conditions
          # (bits and mode), or when max_wait_time is exceeded
          # the async for loop exits.

          status = None
          t_start = time.time()
          async for status in self.yield_status():
            result =  self.bitmask_logic(status_bits=status,mode=mode,mask=mask)
            dt = time.time() - t_start
            if result is True:
               break
            elif dt > max_wait_time:
               self.warn("timeout waiting %s sec for status to change to mask %d mode %s" % (int(mask),mode))
               break
            elif result is None:
               self.error("bitmask logic yields None")
               break

        else:
          status = self.status
          result =  self.bitmask_logic(status_bits=status,mode=mode,mask=mask)

        assert result is not None, "failed to apply mask logic"

        return result

    async def yield_status(self) -> AsyncIterator[ControllerStatus]:
        """Asynchronous generator yield the status of the controller."""

        prev_status = self.status
        yield prev_status # Yield the status on subscription to the generator.
        while True:
            await self.__status_event.wait()
            new_status = self.status
            if new_status != prev_status:
                yield new_status
                prev_status = new_status
            self.__status_event.clear()

    def bitmask_logic(self,status_bits = None, mode=None, mask=None):

        """ evaluate result of masking bits with given mode """

        try:
          assert mode in ['or','nor','and'], "mode must be in [or, nor, and]"
          assert status_bits is not None, "status_bits is None"
          assert mask is not None, "mask is None"
        except Exception as e:
          self.error("exception in bitmask_logic: %s" % e)
          return None

        if mode == 'or': 
           # return true if the mask and the status_bits have any non-zero bits in common
           if status_bits&mask:
              return True

        elif mode == 'nor':
           # return true if the mask and the status word have no non-zero bits in common
           if not (status_bits&mask):
             return True

        else:
           # return true if the mask and the status word have all non-zero mask bits in common
           if status_bits&mask == mask:
             return True

        return False

        
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
            self.debug("new status: %s" % status.get_flags())
            self.__status_event.set()

    async def yield_status(self) -> AsyncIterator[ControllerStatus]:
        """Asynchronous generator yield the status of the controller."""

        prev_status = self.status
        yield prev_status # Yield the status on subscription to the generator.
        while True:
            await self.__status_event.wait()
            new_status = self.status
            if new_status != prev_status:
                yield new_status
                prev_status = new_status
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

        #self.debug("sending command [%s] sync_flag: %s" %\
        #   (command_string,sync_flag))

        command_id = command_id or self._get_id()
        #self.debug("command [%s] id is %d" % (command_string,command_id))

        if command_id > MAX_COMMAND_ID or command_id < 0:
            raise ValueError(
                f"Command ID must be in the range [0, {MAX_COMMAND_ID:d}]."
            )

        command = ArchonCommand(
              command_string,
              command_id,
              controller=self,
              fake=self.fake_controller,
              **kwargs,
        )

        self.__running_commands[command_id] = command

        # non-synchronous I/O
        if not sync_flag:
              self.debug("%s: asynchronously writing command [%s]" % (prefix,command.command_string))
              if not self.fake_controller:
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
              if not self.fake_controller:
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
              if not self.fake_controller:
                self.write(command.raw)

            if not error_msg:
              self.debug("%s: verifying sync" % prefix)
              try:
                await self.ls4_sync_io.sync_verify(command_flag=True)
              except Exception as e:
                error_msg = "Exception verifying sync: %s" % e

        if error_msg is not None:
           self.error("%s: %s" % (prefix,error_msg))
           raise LS4ControllerError(f"Failed running {command_string}: %s" % error_msg)

        #self.debug("done sending command [%s] sync_flag: %s" %\
        #   (command_string,sync_flag))
         
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
            raise ValueError(
                f"Command ID must be in the range [0, {MAX_COMMAND_ID:d}]."
            )

        command = ArchonCommand(
            command_string,
            command_id,
            controller=self,
            fake=self.fake_controller,
            **kwargs,
        )
        self.__running_commands[command_id] = command

         
        if not self.fake_controller:  
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
        #self.info("command_string = %s" % command_string)

        #self.debug("awaiting send_command with command_string = %s" % command_string)
        command = await self.send_command(command_string, **kwargs)
        #self.debug("done awaiting send_command with command_string = %s" % command_string)

        if not command.succeeded():
            if raise_error:
                self.update_status(ControllerStatus.ERROR)
                raise LS4ControllerError(f"Failed running {command_string}.")
            else:
                warnings.warn(f"Failed running {command_string}.", LS4UserWarning)

    async def process_message(self, line: bytes) -> None:
        """Processes a message from the Archon and associates it with its command."""

        match = re.match(b"^[<|?]([0-9A-F]{2})", line)
        if match is None:
            warnings.warn(
                f"Received invalid reply {line.decode()}",
                LS4ControllerWarning,
            )
            return

        command_id = int(match[1], 16)
        if command_id not in self.__running_commands:
            self.warn("command_id [%d] not in running commands" % command_id)
            warnings.warn(
                f"Cannot find running command for {line[0-20]}",
                LS4ControllerWarning,
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
            raise LS4ControllerError(
                f"Command STATUS finished with status {cmd.status.name!r}",
                set_error_status=error,
            )

        system = {}

        if self.fake_controller:
          keywords=self.fake_control.system_keys
        else:
          keywords = str(cmd.replies[0].reply).split()

        for key, value in map(lambda k: k.split("="), keywords):
            system[key.lower()] = value
            if match := re.match(r"^MOD([0-9]{1,2})_TYPE", key, re.IGNORECASE):
                name_key = f"mod{match.groups()[0]}_name"
                system[name_key] = ModType(int(value)).name

        return system

    async def get_device_status(self,\
              update_frame: bool = True,\
              update_power_bits: bool = True) -> dict[str, Any]:

        """Returns a dictionary with the output of the ``STATUS`` command."""

        device_status=None

        cmd = await self.send_command("STATUS", timeout=10)
        if not cmd.succeeded():
            error = cmd.status == ArchonCommandStatus.TIMEDOUT
            raise LS4ControllerError(
                f"Command STATUS finished with status {cmd.status.name!r}",
                set_error_status=error,
            )

        if self.fake_controller:
            device_status = {'powergood':1,'overheat':0,'power':4}
            status_keys=self.fake_control.status_keys
            conf_enable_keys=self.fake_control.conf_enable_keys
            for k in status_keys:
                device_status[k]=0.0
            for k in conf_enable_keys:
                device_status[k]=0
            device_status['mainloop']=0
        else:
          for key_val_str in str(cmd.replies[0].reply).split():
              key_val = key_val_str.split("=")
              key=key_val[0].lower()
              val= key_val[1]
              value = None
              # The timing code uses one of the DIO bits of the XBIAS card (MOD4/DINPUTS) to signal 
              # when it is busy running a main-loop procedure (erasing, purging, clearing, flushing,
              # etc). The STATUS_START_BIT is asserted when the procedure is running, and 
              # cleared when finished. Set keyword 'MAINLOOP' to show the status of this bit
              # (False when asserted, True otherwise)
              # code is in the main loop (finished) or not.
              if "mod4/dinputs" in key:
                 #assert check_int(val), "value for MOD4/DINPUTS [%s] is not an integer" % val
                 value = int(val)
                 device_status['mainloop'] = not ( int(val,2)& STATUS_START_BIT)
              elif check_int(val):
                 value = int(val)
              else:
                 value = float(val)
              device_status[key]=value
                  
        """
        keywords = str(cmd.replies[0].reply).split()
        device_status = {
            key.lower(): int(value) if check_int(value) else float(value)
            for (key, value) in map(lambda k: k.split("="), keywords)
        }
        """

        if update_power_bits:
           await self.power()

        if update_frame:
           if self.fake_controller:
              frame= self.fake_control.get_frame()
           else:
              frame=await self.get_frame()
           device_status['frame']=frame

        device_status['shutter']=self.shutter_enable
        s = self.status
        sd = s.status_dict
        device_status.update(sd)

        return device_status

    async def get_frame(self,max_wait=MAX_FETCH_TIME) -> dict[str, int]:
        """Returns the frame information.

        All the returned values in the dictionary are integers in decimal
        representation.

        max_wait is the timeout waiting for the return from send_command. 
        When am image is being fetched, the send_command may not return
        until the fetch is complete. Keep max_wait = MAX_FETCH_TIME so
        that a timeout does not occur waiting for the return.
        """

        ACS = ArchonCommandStatus
        cmd = await self.send_command("FRAME", timeout=max_wait)
        if not cmd.succeeded():
            raise LS4ControllerError(
                f"Command FRAME failed with status {cmd.status.name!r}"
            )

        keywords = str(cmd.replies[0].reply).split()
        frame = {
            key.lower(): int(value) if "TIME" not in key else int(value, 16)
            for (key, value) in map(lambda k: k.split("="), keywords)
        }

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
            raise LS4ControllerError(
                f"An RCONFIG command returned with code {status!r}"
            )

        if any([len(cmd.replies) != 1 for cmd in done]):
            raise LS4ControllerError("Some commands did not get any reply.")

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
        #self.debug("sending HOLDTIMING command")
        cmd_str = "HOLDTIMING"
        cmd = await self.send_command(cmd_str, timeout=1)
        #self.debug("checking if command succeeded")
        if not cmd.succeeded():
          #seld.debug("command did not succeed")
          self.update_status(ControllerStatus.ERROR)
          raise LS4ControllerError(\
               f"Failed sending {cmd_str} ({cmd.status.name})")
        #self.debug("command succeeded")

    async def release_timing(self):
        cmd_str = "RELEASETIMING"
        cmd = await self.send_command(cmd_str, timeout=1)
        if not cmd.succeeded():
          self.update_status(ControllerStatus.ERROR)
          raise LS4ControllerError(\
               f"Failed sending {cmd_str} ({cmd.status.name})")

    async def reboot(self):
        cmd_str = "REBOOT"
        cmd = await self.send_command(cmd_str, timeout=1)
        if not cmd.succeeded():
          self.update_status(ControllerStatus.ERROR)
          raise LS4ControllerError(\
               f"Failed sending {cmd_str} ({cmd.status.name})")

    async def write_config(
        self,
        input: str | os.PathLike[str] | None = None,
        applyall: bool = False,
        applysystem: bool = False,
        applymods: list[str] = [],
        poweron: bool = False,
        timeout: float | None = None,
        overrides: dict = {},
        trigger_opts: dict = {},
        #notifier: Optional[Callable[[str], None]] = None,
        release_timing: bool = True,
        reset: bool = False
    ):
        """Writes a configuration file to the contoller. Optionally write only trigger options.

        Parameters
        ----------
        input
            The path to the configuration file to load. It must be in INI format with
            a section called ``[CONFIG]``. It can also be a string containing the
            configuration itself.
        applyall
            Whether to run ``APPLYALL`` after successfully sending the configuration.
        applysystem
            Whether to run ``APPLYSYSTEM`` after successfully sending the trigger options
        applymods
            A list of apply commands to send to modules (e.g.,
            ``['LOADTIMING', 'APPLYMOD2']``).
        poweron
            Whether to run ``POWERON`` after successfully sending the configuration.
            Requires applyall=True or "applysystem=True.
        timeout
            The amount of time to wait for each command to succeed.  If `None`, reads
            the value from the configuration entry for
            ``timeouts.write_config_timeout``.
        overrides
            A dictionary with configuration lines to be overwritten. Must be a mapping
            of keywords to replace, including the module name (e.g.,
            ``MOD11/HEATERAP``), to the new values.
        trigger_opts
            A dictionary with trigger options to be overwritten. Must be a mapping
            of keywords to replace, e.g. {"TRIGOUTLEVEL":0, "TRIGOUTFORCE": 1'}
        release_timing
            If True, allow controller to start its timing script after writing config file.
            If False, and "hold_timing()" was previously executed, then the controller will 
            not start the timing script until "release_timing()" is later
            executed. THis allow controllers connected by sync cables to synchronize their
            execution of their timing scripts.
        reset
            IF True/False reset after writing configuration
        """

        ACS = ArchonCommandStatus

        timeout = timeout or self.config["timeouts"]["write_config_timeout"]
        delay: float = self.config["timeouts"]["write_config_delay"]

        poll_on = True

        if input is not None:
          cp = configparser.ConfigParser()

          input = str(input)
          if os.path.exists(input):
              cp.read(input)
          else:
              cp.read_string(input)

          if not cp.has_section("CONFIG"):
              raise LS4ControllerError(
                  "The config file does not have a CONFIG section."
              )

          # Undo the INI format: revert \ to / and remove quotes around values.
          aconfig = cp["CONFIG"]
          lines = []
          for key in aconfig:
              lines.append(key.upper().replace("\\", "/") + "=" + aconfig[key].strip('"'))

          #self.debug("Clearing previous configuration")
          await self.send_and_wait("CLEARCONFIG", timeout=timeout)
          #self.debug("Done clearing previous configuration")

          #self.debug("Sending configuration lines")
          #DEBUG:
          #self.info("configuration lines:")
          #i = 0
          #for l in lines:
          #    self.info("line %05d  %s" % (i,l))
          #    i += 1

          # Stop the controller from polling internally to speed up network response
          # time. This command is not in the official documentation.
          await self.send_command("POLLOFF")
          poll_on = False

          cmd_strs = [f"WCONFIG{n_line:04X}{line}" for n_line, line in enumerate(lines)]
          n_lines = len(cmd_strs)
          i=1
          for line in cmd_strs:
              #self.debug("line %d/%d: %s" % (i,n_lines,line))
              cmd = await self.send_command(line, timeout=timeout)
              if cmd.status == ACS.FAILED or cmd.status == ACS.TIMEDOUT:
                  self.debug("cmd error status is %s" % str(cmd.status))
                  self.update_status(ControllerStatus.ERROR)
                  await self.send_command("POLLON")
                  poll_on = True
                  raise LS4ControllerError(
                      f"Failed sending line {cmd.raw!r} ({cmd.status.name})"
                  )
              await asyncio.sleep(delay)
              i += 1

          self.acf_config = cp
          self.acf_file = input if os.path.exists(input) else None

        # Write MOD overrides. Do not apply since we optionall do an APPLYALL afterwards.

        if overrides and len(overrides) > 0:
           #self.debug("Writing configuration overrides.")
           for keyword, value in overrides.items():
             await self.write_line(keyword, value, apply=False)

        # Write trigger options, if any

        if trigger_opts and len(trigger_opts)>0:
          #self.info("Writing trigger options.")
          for keyword, value in trigger_opts.items():
              await self.write_line(keyword, value, apply=False)

        # Restore polling
        if not poll_on:
          await self.send_command("POLLON")
          poll_on = True

        for mod in applymods:
            #notifier(f"Sending {mod.upper()}")
            await self.send_and_wait(mod.upper(), timeout=5)

        if applysystem:
            #notifier("Sending APPLYSYSTEM")
            await self.send_and_wait("APPLYSYSTEM", timeout=5)

        elif applyall:
            #notifier("Sending APPLYALL")
            await self.send_and_wait("APPLYALL", timeout=5)


            # Reset objects that depend on the configuration file.
            self._parse_params()
            await self._set_default_window_params()

            if poweron:
                #notifier("Sending POWERON")
                await self.power(True)

        if reset:
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
            raise LS4ControllerError("The controller ACF configuration is unknown.")

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
            raise LS4ControllerError(f"Invalid keyword {keyword}")

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

        s = f"WCONFIG{n_line:04X}{line}"

        #self.info("sending %s" % s)

        try:
          cmd = await self.send_command(s)
        except Exception as e:
          self.error("Exception sending command %s" %s)
          pass

        #self.info("done sending %s" % s)
        if cmd.status == ArchonCommandStatus.FAILED:
           self.error("failed sending %s" % s)
        #else:
        #   self.info("success sending %s" % s)

        if cmd.status == ArchonCommandStatus.FAILED:
            raise LS4ControllerError(
                f"Failed sending line {cmd.raw!r} ({cmd.status.name})"
            )

        self.acf_config["CONFIG"][keyword] = value_str

        if apply:
            if isinstance(apply, str):
                apply_cmd_str = apply.upper()
            else:
                if mod is None:
                    raise LS4ControllerError("Apply can only be used with modules.")
                modn = mod[3:]
                apply_cmd_str = f"APPLYMOD{modn}"

            cmd_apply = await self.send_command(apply_cmd_str)
            if cmd_apply.status == ArchonCommandStatus.FAILED:
                raise LS4ControllerError(f"Failed applying changes to {mod}.")

            #self.debug(f"{keyword}={value_str}")


    async def read_line(
        self,
        keyword: str,
        mod: Optional[str] = None,
    ):
        """ 
        Read a single line from  the controller configuration. 

        Parameters
        ----------
        keyword
            The config keyword to read. If ``mod=None``, must include the module
            name (e.g., ``MOD11/HEATERAP``); otherwise the module is added from
            ``mod``. Modules and module keywords can be separated by slashes or
            backlashes.
        mod
            The name of the keyword module, e.g., ``MOD11``.

        """

        if not self.acf_config:
            raise LS4ControllerError("The controller ACF configuration is unknown.")

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
            raise LS4ControllerError(f"Invalid keyword {keyword}")

        n_line = current_keywords.index(keyword)


        s = f"RCONFIG{n_line:04X}"


        try:
          cmd = await self.send_command(s)
        except Exception as e:
          error_msg ="Exception sending command %s" %s
          raise LS4ControllerError(error_msg)

        if cmd.status == ArchonCommandStatus.FAILED:
          self.error("failed sending %s" % s)
          raise LS4ControllerError(
                f"Failed sending line {cmd.raw!r} ({cmd.status.name})"
           )

    async def power(self, mode: bool | None = None):
        """Handles power to the CCD(s). Sets the power status bit.

        Parameters
        ----------
        mode
            If `None`, returns `True` if the array is currently powered,
            `False` otherwise. If `True`, powers n the array; if `False`
            powers if off.
            For all cases, the power-bit of the controller status is updated.

        Returns
        -------
        state : `.ArchonPower`
            The power state as an `.ArchonPower` flag.

        """
        if self.fake_controller:
           power_status= await self.fake_control.power(mode)

           if power_status == ArchonPower.ON:
               self.update_status(ControllerStatus.POWERON)
           else:
               self.update_status(ControllerStatus.POWEROFF)

        else:
          if mode is not None:
              cmd_str = "POWERON" if mode is True else "POWEROFF"
              cmd = await self.send_command(cmd_str, timeout=10)
              if not cmd.succeeded():
                  self.update_status([ControllerStatus.ERROR, ControllerStatus.POWERBAD])
                  raise LS4ControllerError(
                      f"Failed sending POWERON ({cmd.status.name})"
                  )

              await asyncio.sleep(1)

          status = await self.get_device_status(update_power_bits=False,update_frame=False)

          power_status = ArchonPower(status["power"])

          if (
              power_status not in [ArchonPower.ON, ArchonPower.OFF]
              or status["powergood"] == 0
          ):
              if power_status == ArchonPower.INTERMEDIATE:
                  warnings.warn("Power in INTERMEDIATE state.", LS4UserWarning)
              self.update_status(ControllerStatus.POWERBAD)
          else:
              if power_status == ArchonPower.ON:
                  self.update_status(ControllerStatus.POWERON)
              elif power_status == ArchonPower.OFF:
                  self.update_status(ControllerStatus.POWEROFF)

        return power_status

    async def get_mainloop_status(self):

        """
           Returns True if timing code is running through the main loop. 
           Returns False if time code is busy running a procedure.

           The timing code uses one of the DIO bits of the XBIAS card (MOD4/DINPUTS) to signal 
           when it is busy running a main-loop procedure (erasing, purging, clearing, flushing,
           etc). The STATUS_START_BIT is asserted when the procedure is running, and 
           cleared when finished. Set return to to show the status of this bit
           (False when asserted, True otherwise).
        """

        result = False
        device_status=None

        cmd = await self.send_command("STATUS", timeout=10)
        if not cmd.succeeded():
            error = cmd.status == ArchonCommandStatus.TIMEDOUT
            raise LS4ControllerError(
                f"Command STATUS finished with status {cmd.status.name!r}",
                set_error_status=error,
            )

        for key_val_str in str(cmd.replies[0].reply).split():
            key_val = key_val_str.split("=")
            key=key_val[0].lower()
            val= key_val[1]
            value = None
            if "mod4/dinputs" in key:
               #assert check_int(val), "value for MOD4/DINPUTS [%s] is not an integer" % val
               value = check_int(val)
               result = not ( int(val,2)& STATUS_START_BIT)
                
        return result

    async def set_autoclear(self, mode: bool, sample=None):
        """
           Enables or disables autoclearing.
           If sample is True, sample the image pixels when clearing. THis automatically
           update the controller memory buffers with new images as they are acquired.

           IF sample is False, no sampling occurs and the memory buffers are unchanged. 
           However, Sample must be restored to value 1 before exposing images.

           if sample is unspecified, sampling will be assumed to be False if
           mode is True, False otherwise
        """

        error_msg = None
        if mode not in [False,True]:
          error_msg =  "mode must be True or False"
        elif mode:
          error_msg = await self.mainloop.set_auto_function(ML.CLEAR_FUNCTION,sample)
        else:
           # when turning off an autofunction, restore the default unless the 
           # the default is the specified autofunction. In that case, set the 
           # new autofunction to the NONE_FUNCTION
           if self.mainloop.default_function == ML.CLEAR_FUNCTION:
              error_msg = await self.mainloop.set_auto_function(ML.NONE_FUNCTION)
           else:
              error_msg = await self.mainloop.restore()

        return error_msg

    async def set_autoflush(self, mode: bool):
        """Enables or disables autoflush."""

        error_msg = None
        if mode not in [False,True]:
           error_msg =  "mode must be True or False"
        elif mode:
           error_msg = await self.mainloop.set_auto_function(ML.FLUSH_FUNCTION)
        else:
           # when turning off an autofunction, restore the default unless the 
           # the default is the specified autofunction. In that case, set the 
           # new autofunction to the NONE_FUNCTION
           if self.mainloop.default_function == ML.FLUSH.FUNCTION:
              error_msg = await self.mainloop.set_auto_function(ML.NONE_FUNCTION)
           else:
              error_msg = await self.mainloop.restore()

        return error_msg

    async def force_shutter_open(self):
        """ Force shutter open, even when controller is idle """

        self.debug("forcing shutter open")
        await self.write_config(trigger_opts={"TRIGOUTLEVEL":1,"TRIGOUTFORCE":1},\
               applysystem=True)

    async def force_shutter_close(self):
        """ Force shutter closed, even when controller is idle """

        self.debug("forcing shutter closed")
        return await self.write_config(trigger_opts={"TRIGOUTLEVEL":0,"TRIGOUTFORCE":1},\
               applysystem=True)

    async def enable_shutter(self):
        """ Enable shutter during exposures """

        self.debug("enabling exposure shutter")
        return await self.write_config(trigger_opts={"TRIGOUTLEVEL":1,"TRIGOUTFORCE":0},\
               applysystem=True)

    async def disable_shutter(self):
        """ Disable shutter during exposures """

        self.debug("disabling exposure shutter")
        return await self.write_config(trigger_opts={"TRIGOUTLEVEL":0,"TRIGOUTFORCE":1},\
               applysystem=True)

    async def enable_vsub(self):
        """ Disable Vsub power on controller. This make the CCDs insensitive to light 
            Return None on success, error_msg on failure.
        """

        error_msg = None

        if not await self.is_power_on():
          error_msg="CCD biases are not powered on. Turn biases on before enabling V_sub"
        else:
          self.debug("enabling Vsub on CCDs")
          try:
            keyword = VSUB_MODULE + "/" + VSUB_ENABLE_KEYWORD
            value = VSUB_ENABLE_VAL
            await self.write_config(overrides={keyword:value},\
               applymods=[VSUB_APPLY_COMMAND])
          except Exception as e:
            error_msg="exception enabling vsub: %s" % str(e)
          self.debug("done enabling Vsub on CCDs")

        if error_msg is not None:
          self.error(error_msg)

        return error_msg

    async def disable_vsub(self):
        """ Disable Vsub power on controller. This make the CCDs insensitive to light 
            Return None on success, error_msg on failure.
        """

        error_msg = None

        if not await self.is_power_on():
          error_msg="CCD biases are not powered on. Turn biases on before disabling V_sub"
        else:
          self.debug("disabling Vsub on CCDs")
          try:
            keyword = VSUB_MODULE + "/" + VSUB_ENABLE_KEYWORD
            value = VSUB_DISABLE_VAL
            await self.write_config(overrides={keyword:value},\
               applymods=[VSUB_APPLY_COMMAND])
          except Exception as e:
            error_msg="exception disabling vsub: %s" % str(e)
          self.debug("done disabling Vsub on CCDs")

        if error_msg is not None:
          self.error(error_msg)

        return error_msg

    async def reset(self, update_status=True, sync_flag=None, release_timing = True, idle_function = None):
        """
           Resets timing and discards current exposures. 
           This disables all the functions called by the  main loop of the
           timing code.

           If release_timing, start the timing code before returning.

           If self.shutter_enable is True, the shutter control is enabled.

           If update_status, update the the controller status to IDLE 
           and update the power status before returning.

           IF sample is True or False, turn main-loop sampling on/off

        """

        error_msg = None
        if sync_flag is None:
           sync_flag = self.ls4_sync_io.sync_flag

        self._parse_params()

        self.debug("start resetting controller")

        self.debug("hold_timing")
        await self.hold_timing()


        if idle_function is None:
           self.debug("mainloop_autofunction will be default from timing code")
        if idle_function in ML.auto_functions:
           self.debug("setting mainloop_autofunction to %s" %\
                str(idle_function))
           error_msg = await self.mainloop.set_auto_function(auto_function = idle_function)
           if error_msg is not None:
              self.error(error_msg)
        elif idle_function is not None:
           self.warn("unrecognized idle_function: %s" % idle_function)

        # Set timing code flags to zero. This puts the timing code in an idle mode
        # 2024 09 26  WaitCount does nothing in current timing code. But future
        # versions of timing code might use it

        for p in ["Exposures","Readout","AbortExposure","DoFlush","DoPurge","DoErase", "WaitCount"]:
          self.debug("disabling %s" % p)
          await self.set_param(param=p, value=0, sync_flag=sync_flag)


        if self.shutter_enable:
           self.debug("enabling shutter")
           await self.enable_shutter()
        else:
           self.debug("disabling shutter")
           await self.disable_shutter()
        """
        # Reset parameters to their default values.
        if "default_parameters" in self.config["archon"]:
            default_parameters = self.config["archon"]["default_parameters"]
            for param in default_parameters:
                self.debug(f"setting %s to %d" %\
                      (param, default_parameters[param]))
                await self.set_param(param=param, \
                      value=default_parameters[param], sync_flag=sync_flag)
        """

        if release_timing:
            self.debug(f"release_timing .")
            await self.release_timing()

        if update_status:
            #self._status = ControllerStatus.IDLE
            self.update_status (ControllerStatus.IDLE)
            self.debug(f"awaiting self.power()")
            await self.power()  # update power_bit of controller status

        self.debug(f"done with reset")

    def _parse_params(self):
        """Reads the ACF file and constructs a dictionary of parameters."""

        if not self.acf_config:
            raise LS4ControllerError("ACF file not loaded. Cannot parse parameters.")

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
        linecount = int(self.parameters.get("LINECOUNT", -1))
        pixelcount = int(self.parameters.get("PIXELCOUNT", -1))
        lines = int(self.parameters.get("LINES", -1))
        pixels = int(self.parameters.get("PIXELS", -1))
        preskiplines= int(self.parameters.get("PRESKIPLINES", 0))
        postskiplines = int(self.parameters.get("POSTSKIPLINES", 0))
        preskippixels = int(self.parameters.get("PRESKIPPIXELS", 0))
        postskippixels = int(self.parameters.get("POSTSKIPPIXELS", 0))
        overscanpixels = int(self.parameters.get("OVERSCANPIXELS", 0))
        overscanlines = int(self.parameters.get("OVERSCANLINES", 0))
        hbin = int(self.parameters.get("HORIZONTALBINNING", 1))
        vbin = int(self.parameters.get("VERTICALBINNING", 1))

        self.default_window = {
            "linecount": linecount,
            "pixelcount": pixelcount,
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

        new_linecount = (preskiplines+lines+postskiplines+overscanlines) // vbin
        new_pixelcount = (preskippixels+pixels+postskippixels+overscanpixels) // hbin

        if new_linecount != linecount:
           self.warn("default linecount [%d] inconsistent with default preskip,postskip,lines,overscan [%d,%d,%d,%d]" %\
                     (linecount, preskiplines,postskiplines,lines,overscanlines))
           self.default_window["linecount"] =  new_linecount

        if new_pixelcount != pixelcount:
           self.warn("default pixelcount [%d] inconsistent with default preskip,postskip,pixel,overscan [%d,%d,%d,%d]" %\
                     (pixelcount,preskippixels,postskippixels,pixels,overscanpixels))
           self.default_window["pixelcount"] = new_pixelcount

        self.current_window.update(self.default_window)

        if self.fake_controller:
             self.fake_control.update(linecount=new_linecount, pixelcount=new_pixelcount)

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

        #self.debug("%s: setting [%s] to [%d] sync_flag: %s sync_test: %s" %\
        #   (prefix,param,value,sync_flag,sync_test))

        # First we check if the parameter actually exists.
        if len(self.parameters) == 0:
            if self.acf_config is None:
                raise LS4ControllerError("ACF not loaded. Cannot modify parameters.")

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
          #self.debug("%s sending command [%s]" % (prefix,cmd_string))
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
           raise LS4ControllerError(f"Failed setting param {param} to value {value}:  %s" % error_msg)

        self.parameters[param] = value
        #self.debug("%s: done setting [%s] to [%d] sync_flag: %s sync_test: %s" %\
        #   (prefix,param,value,sync_flag,sync_test))
        
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
        linecount: int | None = None,
        pixelcount: int | None = None
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
            warnings.warn("Lines value unknown. Did not set.", LS4UserWarning)

        if pixels >= 0:
            await self.set_param("Pixels", pixels)
        else:
            warnings.warn("Pixels value unknown. Did not set.", LS4UserWarning)

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
            "pixelcount": pixelcount,
            "linecount": linecount
        }


        return self.current_window

    async def expose(
        self,
        exposure_time: float = 1,
        exp_done_callback: Optional[Callable[[str], None]] = None, 
    ) -> asyncio.Task:

        """Integrates the CCD for ``exposure_time`` seconds.

           Returns after the exposure completes.
           Abort will interrupt long integration with optional readout.
        """

        #self.notifier(f"%s: preparing for exposure duration exposure {exposure_time} " % get_obsdate())

        CS = ControllerStatus

        if not await self.is_power_on():
            raise LS4ControllerError("Controller power is off.")
        elif await self.is_power_bad():
            raise LS4ControllerError("Controller power is invalid.")
        elif not await self.is_idle():
            raise LS4ControllerError("The controller is not idle.")
        elif await self.is_readout_pending():
            raise LS4ControllerError(
                "Controller has a readout pending. Read the device or clear."
            )

        await self.reset(release_timing=False,sync_flag=False,idle_function=ML.NONE_FUNCTION)

        if self.ls4_sync_io.sync_flag:
           self.debug(f"syncing up")
           await self.set_param(param="SYNCTEST",value=0)

        # Set integration time in centiseconds (yep, centiseconds).
        self.debug(f"setting IntCS to %d" % int(exposure_time * 100))
        await self.set_param("IntCS", int(exposure_time * 100))

        self.debug(f"setting Exposures to 1")
        await self.set_param("Exposures", 1)

        self.config['expose_params']['actexpt']=0.0
        self.config['expose_params']['read-per']=0.0
        self.timing['expose'].start()

        self.debug(f"sending RELEASETIMING")
        await self.send_command("RELEASETIMING")
        self.debug(f"updating status to EXPOSING and READOUT_PENDING")
        self.update_status([CS.EXPOSING, CS.READOUT_PENDING])

        tm = time.gmtime()
        self.config['expose_params']['date-obs']=get_obsdate(tm)
        self.config['expose_params']['startobs']=get_obsdate(tm)

        #self.notifier(f"%s: starting exposure of duration exposure {exposure_time} " % get_obsdate())
        #async def update_state(shutter_open=None):
        async def update_state():
           dt = 0.0
           done=True
           aborted=False
           tm = time.gmtime()
           t_start=time.time()
           if exposure_time>0.0 and dt < exposure_time:
              #self.notifier(f"%s: waiting %7.3f sec for exposure to end" %\
              #    (get_obsdate(),exposure_time))
              done = False
              aborted = False
              error_msg = None
              while (not done) and (not aborted) and (error_msg is None):

                 dt = time.time()-t_start

                 # if dt < elapsed time and the EXPOSING status bit has been reset, then
                 # an abort has occured.
                
                 if dt < exposure_time:
                   aborted = not await self.check_status(bits = ControllerStatus.EXPOSING,\
                               wait_flag = False)
                   if aborted:
                      self.timing['expose'].end()
                      self.warn("exposure aborted after %7.3f sec" % dt)
                   else:
                      await asyncio.sleep(0.01)
                 else:
                    self.update_status(CS.EXPOSING, 'off')
                    self.timing['expose'].end()
                    done = True
                
                   
           else:
              self.debug(f"update_state: skipping 0-sec exposure loop")

           self.config['expose_params']['actexpt']=self.timing['expose'].period
           self.config['expose_params']['doneobs']=get_obsdate()

           self.update_status(CS.EXPOSING, 'off')
           if exp_done_callback is not None:
             try:
               await exp_done_callback("######### DONE WITH EXPOSURE. NOW READING OUT #########")
             except Exception as e:
               self.error("exception executing exp_done_callback: %s" % e)

           #self.debug(f"update_state: updating status to READOUT_PENDING")
           #self.update_status(CS.READOUT_PENDING)
           self.info("%s: done with exposure: expected : %7.3f, measured: %7.3f" %\
                       (get_obsdate(),exposure_time, self.config['expose_params']['actexpt'])) 

        return await update_state()

    async def abort(self, readout: bool = True):
        """Aborts the current exposure.

        If ``readout=False``, does not trigger a readout immediately after aborting.
        Aborting does not clear the charge.
        """

        if not await self.is_exposing():
           self.warn("Controller is not currently exposing.")
           return
        else:
           self.info("aborting current exposure")

        CS = ControllerStatus

        await self.set_param("ReadOut", int(readout))
        await self.set_param("AbortExposure", 1)

        if readout:
          self.update_status(CS.EXPOSING, "off")

        else:
            self.update_status([CS.EXPOSING,CS.READOUT_PENDING],'off')
            #self.update_status(CS.IDLE)

        return


    async def readout(
        self,
        force: bool = False,
        block: bool = True,
        #delay: int = 0,
        wait_for: float | None = None,
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


        await self.set_param(param="SYNCTEST",value=0)

        if (not force) and await self.check_status([ControllerStatus.READOUT_PENDING,ControllerStatus.IDLE],mode='nor'):
            self.error(f"Controller is not in a readable state.")
            raise LS4ControllerError(f"Controller is not in a readable state.")

        """
        delay = int(delay)

        if delay > 0:
           await self.set_param("WaitCount", delay)
        """


        await self.reset(release_timing=False, update_status=False,sync_flag=False, idle_function = ML.NONE_FUNCTION)


        await self.set_param("ReadOut", 1)


        await self.send_command("RELEASETIMING")

        self.timing['readout'].start()
        self.debug(f"update_status READING")

        if self.fake_controller:
           t = time.time()
           try:
             self.fake_control.update(pixelcount=self.current_window['pixelcount'],\
                                linecount=self.current_window['linecount'])
             # choose next controller buffer ready for writing
             buf = await self.fake_control.check_buffer(op='write')
             assert buf is not None, "failed to find buffer ready for writing"
             # update the completness for wbuf to False.
             self.fake_control.update_frame(wbuf=buf,complete=False)
             self.fake_control.update_read(t=t,waited=0.0)
           except Exception as e:
             error_msg = "Exception starting read of fake controller: %s" % e
             raise LS4ControllerError(error_msg)

        #self.update_status(ControllerStatus.READING, notify=False)
        self.update_status(ControllerStatus.READING)

        self.debug(f"update_status READOUT_PENDING")

        self.update_status(ControllerStatus.READOUT_PENDING, "off")

        if not block:
           return

        #max_wait = self.config["timeouts"]["readout_max"] + delay
        max_wait = self.config["timeouts"]["readout_max"] 

        wait_for = wait_for or 3  # sec delay to ensure the new frame starts filling.
        self.debug(f"sleeping {wait_for} sec to make sure readout has started")

        await asyncio.sleep(wait_for)
        waited = wait_for

        t = time.time()
        if self.fake_controller:
          self.debug("updating read")
          self.fake_control.update_read(t=t,waited = wait_for)
          self.debug("getting frame")
          frame= self.fake_control.get_frame()
          self.debug("done getting frame")
        else:
          frame = await self.get_frame()

          #frame = await self.get_frame()
       
        wbuf = frame["wbuf"]
        self.debug("reading out exposure to buffer %d" % wbuf)
        self.info("reading out exposure to buffer %d" % wbuf)


        dt = 0.0
        status_interval = 1.0
        update_interval = 0.1
        #update_interval = 1.0

        done = False
        timeout = False
        lines_read_prev = -1
        t_start = time.time()
        status_start = time.time()
        while (not done) and (not timeout):
           if waited > max_wait:
              timeout = True
           else:
              # During readout, get_frame will timeout after max_wait sec and
              # return None. Keep checking periodically to see when readout is complete.
              #DEBUG
              if self.fake_controller:
                frame = self.fake_control.get_frame()
              else:
                frame = await self.get_frame()

              if frame[f"buf{wbuf}complete"] == 1:
                 done=True
           if not done:
              if dt > status_interval:
                 status_start = time.time()
                 dt = 0.0
                 pixels_read=frame[f"buf{wbuf}pixels"]
                 lines_read=frame[f"buf{wbuf}lines"]
                 w= int(waited)
                 self.info(f"{w}: frame is not complete: {pixels_read} pixel {lines_read} lines")
                 if lines_read <= lines_read_prev:
                    self.error("ERROR reading out at lines_read = %d" % lines_read)
                    timeout=True
                 else:
                    lines_read_prev = lines_read
              await asyncio.sleep(update_interval)
              t=time.time()
              dt  = t - status_start
              waited = t - t_start
              if self.fake_controller:
                 self.fake_control.update_read(t=t,waited=waited)

        self.timing['readout'].end()
        self.config['expose_params']['read-per']=self.timing['readout'].period
        self.update_status(ControllerStatus.READING,'off')
        self.update_status(ControllerStatus.FETCH_PENDING)

        if done:
           self.debug("done reading out controller in %7.3f sec to buf %d" %\
                (self.timing['readout'].period,wbuf))
           if self.fake_controller:
              self.fake_control.update_read(t=t,waited=waited)
              self.fake_control.update_frame(complete=True)

           if idle_after:
               self.update_status(ControllerStatus.IDLE)
           # Reset autoclearing.
           await self.mainloop.restore()

        elif timeout:
           self.error(f"timeout reading out controller")
           self.update_status(ControllerStatus.ERROR)
           self.error("Timed out waiting for controller to finish reading.")
           raise LS4ControllerError(\
                f"Timed out waiting for controller to finish reading.")

        return wbuf

    @overload
    async def fetch(
        self,
        buffer_no: int = -1,
        frame_info: dict | None = None,
        #notifier: Optional[Callable[[str], None]] = None,
        *,
        return_buffer: Literal[False],
    ) -> numpy.ndarray:
        ...

    @overload
    async def fetch(
        self,
        buffer_no: int = -1,
        frame_info: dict | None = None,
        #notifier: Optional[Callable[[str], None]] = None,
        *,
        return_buffer: Literal[True],
    ) -> tuple[numpy.ndarray, int]:
        ...

    @overload
    async def fetch(
        self,
        buffer_no: int = -1,
        frame_info: dict | None = None,
        #notifier: Optional[Callable[[str], None]] = None,
        return_buffer: bool = False,
    ) -> numpy.ndarray:
        ...

    async def fetch(
        self,
        buffer_no: int = -1,
        frame_info: dict | None = None,
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

        #self.notifier("start fetching data from buffer %d" % buffer_no)

        if await self.is_fetching():
            raise LS4ControllerError("Controller is already fetching")

        if frame_info is None:
          if self.fake_controller:
            frame_info=self.fake_control.get_frame()
          else:
            frame_info = await self.get_frame()

        if buffer_no not in [1, 2, 3, -1]:
            raise LS4ControllerError(f"Invalid frame buffer {buffer_no}")

        if buffer_no == -1:
            if self.fake_controller:
              buffer_no = await self.fake_control.check_buffer(frame_info=frame_info,op='fetch')
              if buffer_no is None:
                error_msg ="failed to find buffer ready for fetching"
                self.error(error_msg)
                self.print_frame(frame=frame_info)
                raise LS4ControllerError(error_msg)

            else:   
              buffers = [
                (n, frame_info[f"buf{n}timestamp"])
                for n in [1, 2, 3]
                if frame_info[f"buf{n}complete"] == 1
              ]
              if len(buffers) == 0:
                raise LS4ControllerError("There are no buffers ready to be read")
              sorted_buffers = sorted(buffers, key=lambda x: x[1], reverse=True)
              buffer_no = sorted_buffers[0][0]
        else:
            if frame_info[f"buf{buffer_no}complete"] == 0:
                raise LS4ControllerError(f"Buffer frame {buffer_no} cannot be read")

        self.update_status(ControllerStatus.FETCHING)
        self.info("fetching exposure from  buffer %d" % buffer_no)

        # Lock for reading
        await self.send_command(f"LOCK{buffer_no}",sync_flag=False)

        width = frame_info[f"buf{buffer_no}width"]
        height = frame_info[f"buf{buffer_no}height"]
        bytes_per_pixel = 2 if frame_info[f"buf{buffer_no}sample"] == 0 else 4
        n_bytes = width * height * bytes_per_pixel
        n_blocks: int = int(numpy.ceil(n_bytes / LS4_BLOCK_SIZE))

        start_address = frame_info[f"buf{buffer_no}base"]

        #self.info("buffer: %d  start_address: %x n_bytes: %d n_blocks: %d " % (buffer_no,start_address,n_bytes,n_blocks))

        raw_offset = frame_info[f"buf{buffer_no}rawoffset"]
        raw_blocks_per_line = frame_info[f"buf{buffer_no}rawblocks"]
        raw_lines = frame_info[f"buf{buffer_no}rawlines"]
        raw_n_bytes = raw_lines*raw_blocks_per_line*LS4_BLOCK_SIZE
        raw_start_address = start_address+ raw_offset


        # Set the expected length of binary buffer to read, including the prefixes.
        self.set_binary_reply_size((LS4_BLOCK_SIZE + 4) * n_blocks)

        cmd_string = f"FETCH{start_address:08X}{n_blocks:08X}"
        #self.notifier ("sending command [%s] with timout=None and sync_flag=False" % cmd_string)
        #cmd: ArchonCommand = await self.send_command(
        #   f"FETCH{start_address:08X}{n_blocks:08X}",
        #   timeout=None,sync_flag=False
        #
        self.debug("cmd_string = %s" % cmd_string)
        self.debug("fake = %s" % self.fake_controller)
        #cmd: ArchonCommand = await self.send_command(command_string=cmd_string, \
        #                           fake=self.fake_controller,timeout=None,sync_flag=False)
        cmd: ArchonCommand = await self.send_command(command_string=cmd_string, \
                                   timeout=None,sync_flag=False)
        #self.notifier ("done sending command [%s] with timout=None and sync_flag=False" % cmd_string)

        # Unlock all
        await self.send_command("LOCK0",sync_flag=False)

        # The full read buffer probably contains some extra bytes to complete the 1024
        # reply. We get only the bytes we know are part of the buffer.

        if self.fake_controller:
           fetch_time = self.fake_control.conf['fetch_time']
           await asyncio.sleep(fetch_time)
           frame = cast(bytes, self.fake_control.buffers[buffer_no-1][0:n_bytes])
        else:
           frame = cast(bytes, cmd.replies[0].reply[0:n_bytes])


        # Convert to uint16 array and reshape.
        dtype = f"<u{bytes_per_pixel}"  # Buffer is little-endian
        arr = numpy.frombuffer(frame, dtype=dtype)
        arr = arr.reshape(height, width)

        # Turn off FETCHING bit
        #self.update_status(ControllerStatus.IDLE)
        self.update_status(ControllerStatus.FETCHING, mode = 'off')

        self.timing['fetch'].end()
        #self.info("time to fetch data : %7.3f sec" % self.timing['fetch'].period)

        self.update_status(ControllerStatus.FETCH_PENDING,'off')

        if self.fake_controller:
          # Mark the buffer as fetched by setting completeness to False (i.e. empty)     
          #self.info("setting current buffer (%d) to empty" % buffer_no)
          self.fake_control.update_frame(buf_index=buffer_no,complete = False)

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
            raise LS4ControllerError("No ids remaining in the pool!")

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
            #raise LS4ControllerError("No ids remaining in the pool!")

        return self._id_pool.pop()

    async def erase(self):
        """Run the LBNL erase procedure."""
 
        erase = None
        self.notifier("erasing.")

        await self.reset(release_timing=False, sync_flag=False)

        self.debug("waiting for mainloop status")
        error_msg = await self.wait_mainloop(30.0)
        if error_msg is None:

            # NOTE: when purge executes, parameter DoErase is decremented within
            # the controller memory. When DoErase reaches 0, the timing code returns
            # to its main loop.

            await self.set_param("DoErase", 1)
            await self.send_command("RELEASETIMING")
            self.update_status(ControllerStatus.ERASING)

            max_erase_time = self.config['timeouts']['erase']
            self.debug("waiting up to %7.3f sec for erase to complete" % max_erase_time)
            error_msg = await self.wait_mainloop(max_erase_time)

        if error_msg:
          self.error(error_msg)

        await self.reset(sync_flag=False)
        self.update_status(ControllerStatus.IDLE)

        # wait a short time for Vsub to stabilize following erase procedure.
        await asyncio.sleep(POST_ERASE_DELAY)

        self.notifier("done erasing.")
        return error_msg

    async def purge(self, fast: bool = True):
        """Runs a single cycle of the e-purge routine.

        A cycle consists of an execution of the e-purge routine followed by a
        chip flushing.

        Parameters
        ----------
        fast
            If `False`, a complete flushing is executed after the e-purge (each
            line is shifted and read). If `True`, a binning factor of 16  is used
            (see set_flush_params()).
        """

        self.notifier("running e-purge.")
        error_msg = None

        self.debug("waiting for mainloop status")
        error_msg = await self.wait_mainloop(30.0)
        if error_msg is None:
            await self.reset(release_timing=False,sync_flag=False)
            await self.set_flush_params(flushcount=1,fast=fast)

            # NOTE: when purge executes, parameter DoPurge is decremented within
            # the controller memory. When DoPurge reaches 0, the timing code returns
            # to its main loop.

            await self.set_param("DoPurge", 1)
            await self.send_command("RELEASETIMING")
            self.update_status(ControllerStatus.PURGING)

            done = False

            max_purge_time = self.config["timeouts"]["purge"]
            if fast:
              max_flush_time = self.config["timeouts"]["fast_flush"]
            else:
              max_flush_time = self.config["timeouts"]["flush"]

            max_time = max_purge_time + max_flush_time

            self.debug("waiting up to %7.3f sec for purge to complete" % max_time)
            error_msg = await self.wait_mainloop(max_time)


        if error_msg:
           self.error(error_msg)

        await self.reset_flush_params()
        await self.reset(sync_flag=False)
        self.update_status(ControllerStatus.IDLE)

        self.notifier("done running e-purge.")

        return error_msg

    async def flush(self, flushcount: int = 1, fast: bool = True):
        """flush the array for flushcount iterations. 
           If fast is True, horizontally shift the charge after every 256
           vertical shifts.
           If fast is false, horizonatall shift the charge after every vertical
           shift.

        Parameters
        ----------
        fast
            If `False`, a complete flushing is executed after the e-purge (each
            line is shifted and read). If `True`, a binning factor of 10 is used.

        """

        error_msg = None

        await self.reset(release_timing=False,sync_flag=False)

        self.debug("waiting for mainloop status")
        error_msg = await self.wait_mainloop(30.0)
        if error_msg is None:
            max_flush_time = self.config["timeouts"]["flush"]
            if fast:
                max_flush_time = self.config["timeouts"]["fast_flush"]

            max_flush_time = max_flush_time * flushcount

            await self.set_flush_params(flushcount=flushcount,fast=fast)
            await self.set_param("DoFlush", 1)
            await self.send_command("RELEASETIMING")
            self.update_status(ControllerStatus.FLUSHING)

            await asyncio.sleep(1.0)
            self.debug("waiting up to %7.3f sec for flush to complete" % max_flush_time)
            error_msg = await self.wait_mainloop(max_flush_time)

        if error_msg:
            self.error(error_msg)

        await self.reset_flush_params()
        self.update_status(ControllerStatus.IDLE)

        self.notifier("done flushing %d times" % flushcount)


        return error_msg


    async def set_flush_params(self,flushcount=1, fast=False):

        assert 'FLUSHCOUNT' in self.parameters, "FLUSHCOUNT not a parameter"
        assert 'FLUSHBIN' in self.parameters, "FLUSHBIN not a parameter"
        assert 'SKIPLINEBINVSHIFT' in self.parameters, "SKIPLINEBINVSHIFT not a parameter"

        await self.set_param("FLUSHCOUNT", int(flushcount))

        if fast:
            await self.set_param("FLUSHBIN", 16)
            await self.set_param("SKIPLINEBINVSHIFT", 256)
        else:
            await self.set_param("FLUSHBIN", 4096)
            await self.set_param("SKIPLINEBINVSHIFT", 1)

    async def reset_flush_params(self):

        assert 'FLUSHCOUNT' in self.parameters, "FLUSHCOUNT not a parameter"
        assert 'FLUSHBIN' in self.parameters, "FLUSHBIN not a parameter"
        assert 'SKIPLINEBINVSHIFT' in self.parameters, "SKIPLINEBINVSHIFT not a parameter"

        await self.set_param("FLUSHCOUNT", self.parameters['FLUSHCOUNT'])
        await self.set_param("FLUSHBIN", self.parameters['FLUSHBIN'])
        await self.set_param("SKIPLINEBINVSHIFT", self.parameters['SKIPLINEBINVSHIFT'])

    async def clean(
        self,
        erase: bool = False,
        n_cycles: int = 10,
        flushcount: int = 3,
        fast: bool = False,
        #notifier: Callable[[str], None] | None = None,
    ):
        """Runs a clean procedure for the LBNL chip.

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
        error_msg = None
        self.debug("start cleaning routine")

        self.debug("waiting for mainloop status")
        error_msg = await self.wait_mainloop(30.0)
        if error_msg is None:
            if erase:
              self.debug("start erasing")
              error_msg = await self.erase()
              self.debug("done erasing")
            if error_msg is None:
              ii = 0
              while (ii < n_cycles) and (error_msg is None):
                 jj = ii + 1
                 self.debug("purging cycle %d of %d" % (jj,n_cycles))
                 error_msg = await self.purge(fast=fast)
                 ii += 1

            if error_msg is None:
              self.debug("final flush with %d cycles" % flushcount)
              error_msg = await self.flush(flushcount=flushcount,fast=fast)

        if error_msg:
           self.error(error_msg)

        await self.reset(sync_flag=False)
        self.update_status(ControllerStatus.IDLE)

        self.debug("done with cleaning routine")

        return error_msg

    async def wait_mainloop(self,max_wait_time = 1.0):
        """ wait up to max_wait_time sec for controller timing code to return to main-loop
            after running a process (flushing, purging, erasing, etc). Return error_msg if
            on timeout or exception
        """

        error_msg = None
        t_start = time.time()
        done = False
        timeout = False
        while (not done) and (not timeout) and (error_msg is None):
          try:
             done =  await self.get_mainloop_status()
          except Exception as e:
             error_msg = "Exception getting mainloop_status: %s" %e

          if error_msg is None:
              dt = time.time() - t_start
              if dt > max_wait_time:
                 timeout = True
              elif not done:
                 await asyncio.sleep(0.1)

        if timeout and not error_msg:
          error_msg = "timeout waiting %7.3f sec for purge to complete" % max_wait_time

        if error_msg:
           self.error(error_msg)

        return error_msg
