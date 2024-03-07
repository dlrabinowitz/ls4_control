#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: David Rabinowitz (david.rabinowitz@yale.edu)
# @Date: 2024-01-16
# @Filename: ls4_controller.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)
#
# This is an extension of the controller.py in sdss-archon 
# distribution (on github)

from __future__ import annotations

import sys
import asyncio

from typing import Callable,Iterable

from archon import log
from archon.controller import ArchonController, ControllerStatus

from . import MAX_COMMAND_ID,FOLLOWER_TIMEOUT_MSEC

__all__ = ["LS4Controller"]


class LS4Controller(ArchonController):

    def __init__(
        self,
        name: str,
        host: str,
        local_addr: tuple = ('127.0.0.1',4242),
        port: int = 4242,
        config: dict | None = None,
    ):
        super(LS4Controller,self).__init__(name=name,host=host,local_addr=local_addr,port=port,config=config)
       
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

        #self.sync_event=None
        self.sync_sem_list = None
        self.sync_sem = None
        self.leader = False
        self.follower_timeout_msec = FOLLOWER_TIMEOUT_MSEC
        self.num_controllers = 0
        self.sync_index = None

        # sync_flag is set when parameters must be synchronously set
        # across controllers. That is when the sync_event and sync_sem
        # objects come into play (see self.sync_set_param() below).

        self.sync_flag = False

    #def set_sync_event(self,sync_event: Event):
    #     self.sync_event=sync_event

    def set_sync_sem_list(self,sync_sem_list: Iterable[Semaphore]):
         self.sync_sem_list=sync_sem_list

    def set_sync_index(self,sync_index: int):
         self.sync_index = sync_index

    def set_lead(self, lead_flag: bool = False):
         self.leader = lead_flag

    def set_sync(self, sync_flag: bool = False):
        self.sync_flag = sync_flag

    def set_num_controllers(self, num_controllers = 0):
        self.num_controllers = num_controllers

    def _get_id(self) -> int:
        """Returns an identifier from the pool."""

        if len(self._id_pool) == 0:
            self._id_pool = set(range(MAX_COMMAND_ID))
            #raise ArchonControllerError("No ids remaining in the pool!")

        return self._id_pool.pop()

    async def erase(self):
        """Run the LBNL erase procedure."""

        log.info(f"{self.name}: erasing.")

        await self.reset(release_timing=False, autoflush=False)

        self.update_status(ControllerStatus.FLUSHING)

        await self.set_param("DoErase", 1)
        await self.send_command("RELEASETIMING")

        await asyncio.sleep(2)  # Real time should be ~0.6 seconds.

        await self.reset()

    async def cleanup(
        self,
        erase: bool = False,
        n_cycles: int = 10,
        fast: bool = False,
        notifier: Callable[[str], None] | None = None,
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
        notifier
            A function to call to output messages (usually a command write method).

        """

        if notifier is None:
            notifier = lambda text: None  # noqa

        if erase:
            notifier("Erasing chip.")
            await self.erase()

        mode = "fast" if fast else "normal"
        purge_msg = f"Doing {n_cycles} with DoPurge=1 (mode={mode})"
        log.info(purge_msg)
        notifier(purge_msg)

        for ii in range(n_cycles):
            notifier(f"Cycle {ii+1} of {n_cycles}.")
            await self.purge(fast=fast)

        await self.set_param("DoPurge", 0)

        flush_msg = "Flushing 3x"
        log.info(flush_msg)
        notifier(flush_msg)

        await self.flush(3)

        await self.reset()

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

        log.info("Running e-purge.")

        if fast:
            await self.set_param("FLUSHBIN", 10)
            await self.set_param("SKIPLINEBINVSHIFT", 220)
        else:
            await self.set_param("FLUSHBIN", 2200)
            await self.set_param("SKIPLINEBINVSHIFT", 1)

        await self.reset(release_timing=False)

        self.update_status(ControllerStatus.FLUSHING)

        await self.set_param("DOPURGE", 1)
        await self.send_command("RELEASETIMING")

        #log.info("self.config = %s" % self.config)
        #
        flush_time = self.config["timeouts"]["flushing"]
        if fast:
            flush_time = self.config["timeouts"]["fast_flushing"]

        await asyncio.sleep(self.config["timeouts"]["purge"] + flush_time)

        await self.set_param("FLUSHBIN", 2200)
        await self.set_param("SKIPLINEBINVSHIFT", 1)

        await self.reset()

        return True

    async def super_set_param(
        self,
        param: str,
        value: int,
        force: bool = False,
    ):
        """ this is a call to the unmodified version of set_param in the
            parent to this clas
        """
        return await super(LS4Controller,self).set_param(param,value,force)


    async def set_param(
        self,
        param: str,
        value: int,
        force: bool = False,
    ):
        """ if sync_flag is true, call the sync-enabled version of set_param
            defined in this class. Otherwise call the unmodifed version encoded
            in the parent to this class
        """
          
        if self.sync_flag:
           return await self.sync_set_param(param,value,force)
        else:
           return await self.super_set_param(param,value,force)


    async def sync_set_param(
        self,
        param: str,
        value: int,
        force: bool,
    ):
        """ follower : 
            1. acquire self.sync_sem
            #2. execute FASTPREPPARAM and FASTLOADPARAM for the specified param/value pair.
            2. execute FASTPREPPARAM for the specified param/value pair.
            3. release self.sync_sem

            leader: 
            1. make sure all the semphores are acquired already
            2. execute FASTPREPPARAM for the specified param/value pair. 
            3. release each follower's sync_sem
            4. acquire each follower's sync_sem
            5. execute FASTLOADPARAM for the specified param/value paira
            6. return.
        """

        error_msg = None
        cmd = None

        if self.leader:
           prefix = "leader %s:" % self.name
        else:
           prefix = "follower %s:" % self.name

        log.info("%s : synchronously setting %s to %d" % (prefix,param,value))

        if self.leader:
              assert self.check_semaphores(lock_flag=True), "not all semaphore are initially locked"
        else:
             log.info("%s acquiring sync_sem" % prefix)
             await self.acquire_semaphores(sync_index=self.sync_index)
             log.info("%s done acquiring sync_sem" % prefix)

        # Here all the controllers send the FASTPREPPARAM. However, because the
        # follower are still waiting for their semaphore to release, the lead
        # sends the FASTPREPPARAM before any of the followers.

        if error_msg is None:
          log.info("%s sending FASTPREPPARAM" % prefix)
          cmd = await self.send_command(f"FASTPREPPARAM {param} {value}")
          if not cmd.succeeded():
             error_msg = "%s failed preparing parameters %s to %s" % (prefix,param,value)
          log.info("%s done sending FASTPREPPARAM" % prefix)

        if self.leader and error_msg is None:
           log.info("%s releasing semaphores" % prefix)
           self.release_semaphores()
           log.info("%s done releasing semaphores" % prefix)

           # In parallel threads, the followers are now sending the FASTPREPPARAM and
           # FASTLOADPARAM commands to the respective controllers. However, the loading
           # in these controllers does not actually occur until the followers have 
           # all synced up again and the lead controller finally send the FASTLOADPARAM command.
           #
           # wait here for the followers to sync up.
           log.info("%s re-acquiring semaphores" % prefix)
           await self.acquire_semaphores()
           log.info("%s done re-acquiring semaphores" % prefix)

           # It is not safe for the lead controller to send
           # the FASTLOADPARAM command. The followers will load the param synchronously.

           if error_msg is None:
             log.info("%s setting param %s to %s" % (prefix,param,value))
             cmd = await self.super_set_param(param=param,value=value,force=force)
             log.info("%s done setting param %s to %s" % (prefix,param,value))

        elif error_msg is None:
           # Here the followers send the FASTLOADPARAM command, but it does
           # not do anything until the lead controller does the same.

           #log.info("%s setting param %s to %s" % (prefix,param,value))
           #cmd = await self.super_set_param(param=param,value=value)
           #log.info("%s done setting param %s to %s" % (prefix,param,value))
           cmd = None

           # Here is where the followers signal the lead controller that they are
           # done sending the FASTPREPPARAM and FASTLOADPARAM commands
           log.info("%s releasing sync_sem" % prefix)
           self.release_semaphores(sync_index=self.sync_index)
           log.info("%s done releasing sync_sem" % prefix)
           
        sys.stdout.flush()
        sys.stderr.flush()

        if error_msg:
           log.error(error_msg)
           raise ValueError(error_msg)

        else:
           return cmd

        
    def check_semaphores(self, lock_flag = True):
        for sync_sem in self.sync_sem_list:
            if sync_sem.locked() != lock_flag:
               return False
        return True

        
    async def acquire_semaphores(self, sync_index: int = -1, timeout_msec:float = -1.0):
        """
           acquire the semaphores in the sync_sem_list
        """
        assert sync_index < self.num_controllers, "sync_index [%d] out of range" % sync_index

        if sync_index > -1:
           await self.sync_sem_list[sync_index].acquire()

        else:
           await asyncio.gather(*(sync_sem.acquire() for sync_sem in self.sync_sem_list))

    def release_semaphores(self, sync_index: int = -1, timeout_msec:float = -1.0):
        """
           release the semaphores in the sync_sem_list
        """
        assert sync_index < self.num_controllers, "sync_index [%d] out of range" % sync_index

        if sync_index > -1:
           self.sync_sem_list[sync_index].release()

        else:
           #asyncio.gather(*(sync_sem.release() for sync_sem in self.sync_sem_list))
           for sync_sem in self.sync_sem_list:
               sync_sem.release()


