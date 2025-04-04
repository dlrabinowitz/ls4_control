#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2021-01-20
# @Filename: tools.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from __future__ import annotations

import asyncio
import os
import pathlib
import socket
from subprocess import CalledProcessError
import time
from archon.ls4.ls4_control import LS4_Control
from . import ABORT_EXPOSURE_FILE, ABORT_SERVER_FILE

class LS4_Abort:
    """ monitor and handle aborts.

        When abort_file appears, this is a signal to abort any ongoing exposure.

        If abort_server_file appears, this is a signal to abort any ongoing exposure
        and to abort the command server and exit.
    """

    def __init__(self,abort_file=None, abort_server_file=None,ls4_control = None):

        assert ls4_control is not None, "ls4_control is not instantiated"
        assert isinstance(ls4_control,(LS4_Control)), "ls4_control is not an instance of LS4_Control"

        self.ls4_control = ls4_control

        self.ls4_logger = self.ls4_control.ls4_logger

        self.info = self.ls4_logger.info
        self.debug = self.ls4_logger.debug
        self.warn= self.ls4_logger.warn
        self.error= self.ls4_logger.error
        self.critical= self.ls4_logger.critical


        if abort_file is None:
           abort_file = ABORT_EXPOSURE_FILE
        if abort_server_file is None:
           abort_server_file = ABORT_SERVER_FILE

        self.abort_file = abort_file
        self.abort_server_file = abort_server_file

        if os.path.exists(abort_file):
          os.remove(abort_file)

        if os.path.exists(abort_server_file):
          os.remove(abort_server_file)

        # when self.abort is True, this signals any ongoing exposure
        # to expire prematurely.
        self.abort = False

        # when self.abort_server is True, this also signals the command server
        # to exit (equivalent to "shutdown" command)

        self.abort_server = False

        # shutdown_flag is asserted by command server when it is commanded to shutdown
        self.shutdown_flag = False
  
    def shutdown(self):
        self.shutdown_flag=True

    async def clear_exposure_abort(self):
        """ clear exposure abort flag """

        self.abort = False
        await self.ls4_control.clear_abort()

    def clear_server_abort(self):
        """ clear server abort flag """
        self.abort_server = False

    def check_abort(self):
        """ check if abort_file or abort_server_file exists. 
            If so, assert self.abort or self.abort_server, respectively
        """

        error_msg = None

        if os.path.exists(self.abort_server_file):
           self.debug("abort server file found")
           os.remove(self.abort_server_file)
           self.abort_server=True
           self.abort=True

        if os.path.exists(self.abort_file):
           self.debug("abort file found")
           os.remove(self.abort_file)
           self.abort=True

        return error_msg

    async def watchdog(self):
        """ while exposure is ongoing, keep checking for abort.
            If one occurs, excute the abort function of ls4_control.
            Exit for any of 3 reasons:
               (1) the exposure ends
               (2) the abort function is executed
               (3) there is an error
        """

        error_msg = None
        self.debug("abort watchdog starting")


        while (not self.abort_server) and (not self.shutdown_flag):
          await asyncio.sleep(1)
          #self.debug("watchdog checking status ...")
          if error_msg is not None:
            self.error("%s" % str (error_msg))
          else:
            #self.debug("checking for abort")
            try:
              error_msg = self.check_abort()
            except Exception as e:
              error_msg = "Exception executing check_abort: %s" % e

            if self.abort and not error_msg:
               self.warn("aborting ongoing exposure")
               error_msg = await self.ls4_control.abort(readout=False)
               self.warn("done aborting ongoing exposure")
               await self.clear_exposure_abort()

  
        if self.abort_server:
          self.debug("server aborted. watchdog exiting")
        elif self.shutdown_flag:
          self.debug("server shutdown. watchdog exiting")
   
