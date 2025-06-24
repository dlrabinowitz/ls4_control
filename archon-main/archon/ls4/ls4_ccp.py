############################
# -*- coding: utf-8 -*-
#
# @Author: David Rabinowitz (david.rabinowitz@yale.edu)
# @Date: 2025-06-25
# @Filename: ls4_ccp.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)
#
# Python code defining LS4_CCP class
# This provides fron-end interface for control of the LS4 camera.
#
# An instance of LS4_CCP initializes and configures the LS4 camera using
# the LS4_Control class. Initialization parameters can be provided as command-line
# arguments at start up, or by reading these same configuration parameters from a
# startup file.
#
# LS4_CCP waits for commands over a dedicated socket port on the host machine (port 5000).
# After each execution, LS4_CCP sends a reply (DONE + message or ERROR + message).
# Commands (with arguments) and replies must have a total byte length < 1024. LS4_CCP
# handles only one client connection at a time.
#
# The commands are of the form "command_str arg1 arg2 ..." where the expected
# arguments are specified in pre-defined order (see ls4_commands.py).
# After sending a command, the client program must wait for and read back the
# reply before closing the connection. 
#
# typical implementation
#
# server side:
#
#   initialize configuration, ls4_conf{}:
#       read keyword/value pairs from command line or config file
#
#   instantiate LS4_CCP using ls4_conf:
#        ls4_ccp = LS4_CCP(ls4_conf)
#
#   initialize the instance of LS4_CCP
#        list_ccp.init()
#
#   run ls4_ccp
#        ls4_ccp.run()
#
# The server will exit when it received the "shutdown" command or encounters
# an un-recoverable error. The "restart" command will re-initialize ls4_ccp
# and restart the command server. The "reboot" command will reboot the controllers
# before restarting them
#
# client side:
#   
#   open connection to LS4_CCP port
#   
#   send commands to LS4_CCP port and read back replies
#
#   send "shutdown" command when done
#
############################

import sys
import os
import asyncio
import time
import argparse
import json
from archon.ls4.ls4_control import LS4_Control
from archon.ls4.ls4_commands import LS4_Commands
from archon.ls4.ls4_control import get_obsdate
from archon.ls4.ls4_status import LS4_Status
from archon.controller.ls4_logger import LS4_Logger
from archon.ls4.ls4_command_server import LS4_Command_Server
from archon.tools import check_bool_value
from archon.tools import get_obsdate
from archon.ls4.ls4_abort import LS4_Abort


class LS4_CCP():
    def __init__(self,logger=None,ls4_conf_file=None, ls4_conf=None,parse_args=False):
       """ 
       instantiated LS4_CCP, optionally providing:

           logger - an instance of LS4_Logger for printing diagnostic messagves

           ls4_conf_file - a JSON-formatted file with values for configuration parameters

           ls4_conf - a dictionary of values for each configuration parameter

           parse_args - True/False to read configuration paramters from the command line.
 
       Any combination of configuration options can be provided. The order in which parameters
       will be initialized is (1) ls4_conf, (2) ls4_conf_file, and (3) command-line.
       If none of these option are specified, default parameter values will be used (see ls4_conf.py).
       """

       self.ls4_ctrl = None 
       self.ls4_conf = ls4_conf
       self.ls4_conf_file = ls4_conf_file
       self.parse_args=parse_args
       self.ccp_status = LS4_Status()
       self.ls4_abort=None
       self.ccp_status.update({'abort':False})

       #instantiated a default logger if no instance is provided
       if logger is None:
         self.logger = LS4_Logger(name="LS4_CCP")
       else:
         self.logger=logger

       # logger shortcuts
       self.info = self.logger.info
       self.debug= self.logger.debug
       self.warn = self.logger.warn
       self.error= self.logger.error
       self.critical= self.logger.critical


    async def set_sync(self,sync=True):
        """ set controller mode to sync = True or False """

        error_msg = None

        assert self.ls4_ctrl is not None, "ls4_ctrl is not instantiated"
        assert sync in [True,False], "sync is must be True or False"

        try:
           await self.ls4_ctrl.set_sync(sync=sync)
        except Exception as e:
           error_msg = "exception setting sync to %s" % sync

        return error_msg

    async def init(self,restart=False,reboot=False):

        """ close and delete any existing instance of ls4_ctrl,
            re-instantiate, and then re-initialize

            If restart or reboot is True, stop the existing instance
            of ls4_ctrl before rebooting (if reboot = True) and 
            restarting.
        """

        error_msg = None

        if self.logger is None:
          self.logger = LS4_Logger(name="LS4_CCP")

        self.logger.info("initializing LS4_CCP with restart/reboot = %s/%s" % (restart,reboot))

        if (restart or reboot) and (self.ls4_ctrl is not None):
          self.info("stopping ls4_ctrl")
          try:
            await self.ls4_ctrl.stop()
            del self.ls4_ctrl
            self.ls4_ctrl=None
            self.logger = None
            self.ls4_conf = None
          except Exception as e:
            error_msg = "Exception closing and deleting ls4_ctrl: %s" % e
            self.error(error_msg)

        if error_msg is None:
          self.info("re-starting ls4_ctrl")
          if self.logger is None:
            self.logger = LS4_Logger(name="LS4_CCP")

          self.info("instantiating LS4_Control")
          try:
            self.ls4_ctrl = LS4_Control(logger=self.logger,ls4_conf_file=self.ls4_conf_file,\
                              init_conf=self.ls4_conf,parse_args=self.parse_args)
            if self.ls4_ctrl is None:
               error_msg = "failed to instantiate LS4_Control"
            else:
               self.ls4_conf = self.ls4_ctrl.ls4_conf
          except Exception as e:
            error_msg = "exception instantiating LS4_Control: %s" % e

        if error_msg is None:
          self.logger = self.ls4_ctrl.ls4_logger
          self.info = self.logger.info
          self.debug= self.logger.debug
          self.warn = self.logger.warn
          self.error= self.logger.error
          self.critical= self.logger.critical


        if error_msg is None:
           self.ls4_ctrl.info("initializing camera with reboot = %s" % reboot)
           try:
             await self.ls4_ctrl.initialize(reboot=reboot)
           except Exception as e:
             error_msg="failed to initialize LS4_Control: %s" % e

        if error_msg is None:
           self.ls4_ctrl.info("starting camera")
           try:
             await self.ls4_ctrl.start()
           except Exception as e:
             error_msg="failed to initialize LS4_Control: %s" % e

        if error_msg is not None:
           if self.logger is not None:
             self.logger.error(error_msg)
           else:
             print(error_msg)

        return error_msg

    async def close(self,power_down=True):

        """ put controller in auto-clear mode, close ls4_ctrl instance,
            and delete the instance
        """

        assert self.ls4_ctrl is not None, "ls4_ctrl is not instantiated"

        self.info("closing controllers")
        error_msg = None

        
        self.debug("unsyncing controllers")
        error_msg = await self.set_sync(sync=False)
        if error_msg:
          self.error(error_msg)
        

        self.debug("start autoclearing")
        try:
          await self.ls4_ctrl.start_autoclear()
        except Exception as e:
          error_msg = "Exception starting autoclear: %s" % e
          self.error(error_msg)

        self.debug("stopping controllers")
        try:
          await self.ls4_ctrl.stop(power_down=power_down)
        except Exception as e:
          error_msg = "Exception stopping controllers: %s" % e
          self.error(error_msg)

        return error_msg

    async def run(self, restart=False, reboot=False):

      """ 
        initialize LS4_CCP and start controllers. 
        If restart is True, close already running instance of LS4_CCP and then restart.
        If restart is True and reboot is True, then reboot the controllers before 
        restarting
      """

      if restart:
        self.info("re-initializing LS4_CCP and re-starting controllers with reboot = %s" % reboot)
      else:
        self.info("initialize LS4_CCP and start controllers")

      ls4_command_server = None
      ls4_status_server = None
      command_function = None
      command_dict = None
      server_dict = None
      error_reply = None
      done_reply = None
      error_msg = None

      self.ls4_abort=None
      
      assert 'sync' in self.ls4_conf, "sync keyword missing from config"
      assert 'server_name' in self.ls4_conf, "server_name keyword missing from config"
      assert 'server_port' in self.ls4_conf, "server_port keyword missing from config"
      assert 'reset' in self.ls4_conf, "reset keyword missing from config"
      assert 'power_down' in self.ls4_conf, "power_down keyword missing from config"

      self.sync_controllers = check_bool_value(self.ls4_conf['sync'],True)

      # reset means to reset controllers, close them, and exit. No commands are executed
      self.reset= check_bool_value(self.ls4_conf['reset'],True)
      # initial_reboot means to reboot controllers before configuring then.
      self.initial_reboot= check_bool_value(self.ls4_conf['initial_reboot'],True)
      # power_done = True means power-off the camera biases before exiting
      self.power_down= check_bool_value(self.ls4_conf['power_down'],True)

      if reboot | self.initial_reboot:
         reboot = True
         self.init_reboot = False

      if restart or reboot:
         self.reset = True
         self.warn("restarting controllers with reboot = %s" % reboot)

         self.info("Initializing LS4_CPP")
         error_msg=await self.init(restart=restart,reboot=reboot)

         self.ccp_status.update({'restart':False})
         self.ccp_status.update({'reboot':False})
         
      if error_msg is None and not self.reset:
         # ls4_abort is used to abort functions when special files appear at /tmp
         self.ls4_abort=LS4_Abort(ls4_control = self.ls4_ctrl)
         self.info("Instantiating LS4_Commands")
         try:
           ls4_commands = LS4_Commands(ls4_control=self.ls4_ctrl,ls4_abort = self.ls4_abort)
           command_function = ls4_commands.command_function
           command_dict = ls4_commands.command_dict
           status_dict = {}
           status_dict['status'] = ls4_commands.command_dict['status']
           error_reply = ls4_commands.error_reply
           done_reply = ls4_commands.done_reply
         except Exception as e:
           error_msg = "Exception instantiating LS4_Commands: %s" % e

      #setup command server for general commands
      if error_msg is None and not self.reset:
        server_name=self.ls4_conf['server_name']
        server_port=self.ls4_conf['server_port']
        server_bufsize=1024
        self.info("Instantiating LS4_Command_Server for commands on port %d" % server_port)

        async def command_fnc(command=None,arg_value_list=None,reply_list=None):
           await command_function(command=command,arg_value_list=arg_value_list,reply_list=reply_list)

        try:
          ls4_command_server = LS4_Command_Server(host=server_name,port=server_port,\
              maxbufsize=server_bufsize,ls4_abort=self.ls4_abort,
              command_fnc=command_fnc,logger=self.logger,server_status=self.ccp_status,\
              command_dict=command_dict,error_reply=error_reply,done_reply=done_reply)
        except Exception as e:
          error_msg = "Exception instantiating command server: %s" % e
      
      #"""
      #setup server for status command only
      if error_msg is None and not self.reset:
        server_name=self.ls4_conf['server_name']
        server_port=self.ls4_conf['status_port']
        server_bufsize=1024
        self.info("Instantiating LS4_Command_Server for status only on port %d" % server_port)

        async def status_fnc(command=None,arg_value_list=None,reply_list=None):
           await command_function(command=command,arg_value_list=arg_value_list,reply_list=reply_list)

        try:
          ls4_status_server = LS4_Command_Server(host=server_name,port=server_port,\
              maxbufsize=server_bufsize,ls4_abort=self.ls4_abort,\
              command_fnc=status_fnc,logger=self.logger,server_status=self.ccp_status,\
              command_dict=status_dict,error_reply=error_reply,done_reply=done_reply,
              status_only = True)
        except Exception as e:
          error_msg = "Exception instantiating status server on port %d: %s" % (server_port,e)
      #"""     

      if error_msg is None and not self.reset:
        self.info("Running command and status servers")
        try:
          #await ls4_command_server.run()
          #await asyncio.gather(ls4_command_server.run(),self.ls4_abort.watchdog())
          #await asyncio.gather(ls4_command_server.run(),ls4_status_server.run())
          await asyncio.gather(ls4_status_server.run(),\
                               ls4_command_server.run(),\
                               self.ls4_abort.watchdog())
        except Exception as e:
          error_msg = "Exception running command and status servers: %s" % e

        if self.ls4_abort.abort_server:
           self.warn("aborting")

      if error_msg:
        self.error(error_msg)

      if self.ls4_ctrl is not None:
        await self.close(power_down=self.power_down)

      self.info("exiting" )

      if (ls4_command_server is None) and not self.reset:
         self.ccp_status.update({'error':True})

      return self.ccp_status.get()
   
if __name__ == "__main__":
   
  async def main_loop():

      abort = False # set to True if external abort triggered
      error_msg = None
      status = None
      logger=None
      ls4_ccp=None
      done=False

      print("instantiating LS4_CCP")
      try:
        ls4_ccp = LS4_CCP(parse_args=True)
        logger=ls4_ccp.logger
      except Exception as e:
        error_msg = "exception instantiating LS4_CCP: %s" % e
     
      print("initializing camera")
      try:
        error_msg = await ls4_ccp.init(restart=False)
      except Exception as e:
        error_msg = "exception initializing camera: %s" % e

      restart = False
      print("starting command loop")
      while not done and error_msg is None:
        done=True
        status=None
        try:
          status=await ls4_ccp.run(restart)
          if status is None:
            error_msg = "server status is None"
          elif 'error' in status and status['error']:
            error_msg = "error  running ls4_ccp"
        except Exception as e:
          error_msg = "exception running ls4_ccp: %s" %e

        if restart:
            restart = False

        if status is None:
           error_msg = "server status is None"
        elif 'restart' in status and status['restart']:
           logger.info("restart requested")
           restart = True
           done = False
        elif 'shutdown' in status and status['shutdown']:
           logger.info("shutdown requested")

      if error_msg is not None:
        if logger is not None:
          logger.error(error_msg)
        else:
          print(error_msg)

      print("done")
                
  asyncio.run(main_loop())
