# LS4_CCP class for front-end control of the LS4 camera.
#
# This file defines the LS4_CCP, the front-end iterface for controlling the LS4
# camera. An instance of LS4_CCP initializes and configures the LS4 camera using
# the LS4_Control class. Initialization parameters can be provided as command-line
# arguments at start up, or by reading these same configuration parameters from a
# startup file.
#
# LS4_CCP waits for commands over a dedicated socket port on the host machine (port 5000).
# After each execution, LL4_CCP sends a reply (DONE + message or ERROR + message).
# Commands (with arguments) and replies must have a total byte length < 1024. LS4_CCP
# handles only one client connection at a time.
#
# The commands are of the form "command_str arg1 arg2 ..." where the expected
# arguments are specified in pre-defined order (see LS4_CCP.command_dict).
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
#   run ls4_ccp
#        ls4_ccp.run()
#
# The server will exit when it received the "shutdown" command or encounters
# an un-recoverable error. The "restart" command will re-initialize ls4_ccp
# and restart the command server
#
# client side:
#   
#   open connection to LS4_CCP port
#   
#   send commands to LS4_CCP port and read back replies
#
#   send "shutdown" command when done
#

import sys
import os
import asyncio
import time
import argparse
import json
from archon.ls4.ls4_control import LS4_Control
from archon.controller.ls4_logger import LS4_Logger
from archon.ls4.ls4_command_server import LS4_Command_Server

DONE_REPLY = "DONE"
ERROR_REPLY = "ERROR"
SHUTDOWN_COMMAND = "shutdown"
RESTART_COMMAND = "restart"

def str_to_bool(s):
    val = False
    if s in ['True','true','TRUE',True]:
       val = True
    return val

def namelist(s):
    """ return a list of separate strings given a single string
        of items separated by commas
    """
    return s.split(",")

class LS4_CCP():

    done_reply = DONE_REPLY
    error_reply = ERROR_REPLY
    shutdown_command= SHUTDOWN_COMMAND
    restart_command = RESTART_COMMAND

    # commands understood by LS4_CCP

    command_dict={\
        'init':{'args':[],'comment':'initialize camera controller'},\
        'open':{'args':[],'comment':'open the camera shutter'},\
        'close':{'args':[],'comment':'close the camera shutter'},\
        'status':{'args':[],'comment':'return camera status'},\
        'flush':{'args':['flush_time'],'comment':'flush the camera for specified time'},\
         #'r':{'args':['num_lines','file_root'],\
         #    'comment':'readout num_lines from camera and write to file'},\
        'h':{'args':['key_word','value'],\
             'comment':'add keyword/value to image fits header'},\
        'e':{'args':['shutter','exptime','fileroot','exp_mode'],\
            'comment':'expose for exptime sec with shutter open (True,False) using exp_mode and saved to fileroot'},\
        'help':{'args':[],'comment':'list commands and their args'},\
        }

    def __init__(self,ls4_conf=None,ls4_conf_file=None):

       assert [ls4_conf,ls4_conf_file] != [None,None], "must specify ls4_conf or ls4_conf_file"

       self.ls4_ctrl = None 
       self.logger = LS4_Logger(name="LS4_CCP")
       self.ls4_conf={}
       error_msg = None
       
       if ls4_conf is not None:
          self.ls4_conf.update(ls4_conf)
       else:
          try:
            error_msg = self.read_conf_file(ls4_conf_file)
          except Exception as e:
            error_msg = "Exception loading conf file %s: %s" %\
                  (ls4_conf_file,e)
           
       if error_msg is not None:
          self.logger.error(error_msg)

       assert error_msg is None, error_msg

       self.logger.info("conf: %s" % str(self.ls4_conf))
       
    def read_conf_file(self,input=None):

        """read in an ls4_conf json file"""

        error_msg = None
        conf={}

        if  input is None:
            error_msg =  "input file is None"


        if error_msg is None:
          try:
            fin=open(input,"r")
          except Exception as e:
            error_msg = "Exception opening conf file %s: %s" %\
                 (input,e)

        if error_msg is None:
          try:
            data=json.load(f)
          except Exception as e:
            error_msg = "Exception reading json data from conf file %s: %s" %\
                 (input,e)

        if error_msg is None:
           for key in data:
               entry=data[key]
               type=entry['type']
               if type == 'namelist':
                  conf[key]=namelist(entry['val'])
               else:
                  conf[key]=entry['val']

        if error_msg is not None:
          self.logger.error(error_msg)
        else:
          ls4_conf=conf
       
        return error_msg

     
    async def command_function(self,command=None,command_args=None,reply_list=None):

        assert self.ls4_ctrl is not None, "ls4_ctrl is not instantiated"
        assert command is not None,"unspecified command"
        assert command_args is not None,"unspecified command_args"
        assert reply_list is not None,"unspecified reply_list"
         
        reply_list[0]=self.done_reply
        error_msg = None
       
        self.logger.info("%s command [%s] args [%s]" %\
                     (self.ls4_ctrl.get_obsdate,command,str(command_args)) )

        if command not in self.command_dict:
           error_msg = "unexpected command [%s] with args [%s]" % (command,str(command_args))

        elif command == 'init':
           self.logger.info("resetting and re-initializing ls4 control program")
           try:
              #await self.ls4_ctrl.reset()
              #await self.ls4_ctrl.initialize()
              error_msg = await self.init()
           except Exception as e:
              error_msg = "exception initializing ls4_control_program %s" %e

           if error_msg:
              self.logger.error(error_msg)
              reply_list[0]=self.error_reply + " " + error_msg

        elif command == 'open_shutter':
           self.logger.info("opening shutter")
           await asyncio.sleep(2)

        elif command == 'close_shutter':
           self.logger.info("closing shutter")
           await asyncio.sleep(2)

        elif command == 'status':
           self.logger.info("getting control status")
           reply_list[0] = self.done_reply + " " + str(self.ls4_ctrl.status)
           self.logger.info("done getting control status")

        elif command == 'flush':
           flush_args = command_args
           if command_args[0].lower() == 'default':
              flush_args[0] = "%7.3f" % ls4_conf['flush_time']

           self.logger.info("flushing with args [%s]" % str(command_args))
           error_msg = await self.flush(flush_args=flush_args)
           self.logger.info("done flushing with args [%s]" % str(flush_args))

        #elif command == 'r':
        #   self.logger.info("reading CCD images")
        #   await asyncio.sleep(2)

        elif command == 'h':
           self.logger.info("modifying image header")
           extras = {command_args[0]:command_args[1]}
           self.ls4_ctrl.set_extra_header(extras)

        elif command == 'e':

           self.logger.info("taking exposure with args [%s]" % str(command_args))
           error_msg = await self.expose(expose_args=command_args)
           self.logger.info("done taking exposure with args [%s]" % str(command_args))

        elif command == 'help':
           self.logger.info("printing command help")
           reply_list[0] = self.done_reply + self.help_string()
           self.logger.info("done printing command help")

        if error_msg is not None:
           self.logger.error(error_msg)
           reply_list[0] = self.error_reply + " " + error_msg

        self.logger.info("%s command [%s] args [%s] reply [%s]" %\
              (self.ls4_ctrl.get_obsdate(),command,command_args,reply_list[0]))

    def help_string(self):

        help_str="\n"
        for command in self.command_dict:
            c=self.command_dict[command]
            help_str += "%s:  " % command
            help_str += "args: %s  " % c['args']
            help_str += "# %s\n" % c['comment']
 
        return help_str

    async def sync(self):

        error_msg = None
        if self.sync_controllers:
          try:
            await self.ls4_ctrl.sync()
          except Exception as e:
            error_msg = "Exception syncing: %s" % e
            self.logger.error(error_msg)

        return error_msg


    async def unsync(self):

        error_msg = None
        if self.sync_controllers:
          try:
            await self.ls4_ctrl.unsync()
          except Exception as e:
            error_msg = "Exception unsyncing: %s" % e
            self.logger.error(error_msg)

        return error_msg

    async def flush(self,flush_args=None):
        """ continuously read out ccds for flush_time sec """

        assert self.ls4_ctrl is not None, "ls4_ctrl is not instantiated"
        
        error_msg = None

        flush_time = float(flush_args[0])

        try:
          await self.ls4_ctrl.flush(flush_time)
        except Exception as e:
          error_msg = "Exception flushing CCDs for %7.3f sec: %s" % (flush_time,e)

        return error_msg

    async def expose(self,expose_args = None):

        """ take an exposure with exptime, shutter state, fileroot, and 
            exposure mode given by expose_args
        """

        # Notes:
        # A complete exposure consists of two operations:
        #    acquire: expose and readout to controller memory
        #    fetch from contoller memory to host memory
        #
        # To minimize the interval between sucessive exposures, the fetching 
        # of a previously acquired image can occur during the acquisition of 
        # the next.
        #
        # in the call to expose(), the sequencing is controlled
        # by the op_mod expression:
        #
        #   exp_mode_single : acquire and fetch the same image in sequence
        #   exp_mode_first  : acquire a new image but do not fetch
        #   exp_mode_next   : fetch previous image while acquiring the next
        #   exp_mode_last   : fetch previous image and do not acquire
        #
        # Use exp_mode_single when only one image is required.
        #
        # For a sequence of exposures, use exp_mode_first for the first image, exp_mode_next up until
        # the last, and then use exp_mode_last

        assert self.ls4_ctrl is not None, "ls4_ctrl is not instantiated"

        error_msg = None

        shutter = str_to_bool(expose_args[0])
        exptime = float(expose_args[1])
        fileroot = expose_args[2]
        exp_mode = expose_args[3]
        exp_number = self.ls4_ctrl.image_count

        save = self.ls4_conf['save'] # must be True to save exposures to disk

        #DEBUG
        if 1:
        #try:
          self.logger.info("%s: exposing image: %d exptime: %7.3f shutter: %s  mode: %s fileroot: %s" %\
                      (self.ls4_ctrl.get_obsdate(),exp_number,exptime,shutter,exp_mode,fileroot))
          await self.ls4_ctrl.expose(exptime=exptime,exp_number=exp_number,
                  exp_mode = exp_mode, save=save, enable_shutter=shutter)
          self.logger.info("%s: done exposing with exptime: %7.3f shutter: %s  mode: %s fileroot: %s" %\
                      (self.ls4_ctrl.get_obsdate(),exptime,shutter,exp_mode,fileroot))
        else:
        # except Exception as e:
          error_msg = "Exception exposing with exptime: %7.3f shutter: %s  mode: %s fileroot: %s : %s" %\
                      (exptime,shutter,exp_mode,fileroot,e)
          self.logger.error(error_msg)

        return error_msg

    async def initialize(self):

        """ initialize and start the ls4_ctrl program after ls4_ctrl has
            been instantiated
        """

        assert self.ls4_ctrl is not None, "ls4_ctrl is not instantiated"
        error_msg = None

        if error_msg is None:
          self.logger.info("Initializing LS4_Control")
          #DEBUG
          #try:
          if 1:
            await self.ls4_ctrl.initialize()
          #except Exception as e:
          else:
            error_msg = "Exception initializing ls4_ctrl: %s" % e
            self.logger.error(error_msg)


        if error_msg is None:
          self.logger.debug("unsyncing controllers")
          error_msg = await self.unsync()

        if error_msg is None:
          self.logger.info("Starting  LS4_Control")
          try:
            await self.ls4_ctrl.start()
          except Exception as e:
            error_msg = "Exception starting controllers: %s" % e
            self.logger.error(error_msg)

        return error_msg

    async def init(self):

        """ close and delete any existing instance of ls4_ctrl,
            re-instantiate, and then re-initialize
        """

        error_msg = None

        if self.logger is None:
           self.logger = LS4_Logger(name="LS4_CCP")

        self.logger.info("re-starting ls4_ctrl")

        if self.ls4_ctrl is not None:
           self.logger.info("closing ls4_ctrl")
           try:
             #await close(self.ls4_ctrl)
             del self.ls4_ctrl
             self.logger = None
           except Exception as e:
             error_msg = "Exception closing and deleting ls4_ctrl: %s" % e
             self.logger.error(error_msg)

        if error_msg is None:
           if self.logger is None:
             self.logger = LS4_Logger(name="LS4_CCP")

           self.logger.info("instantiating ls4_ctrl")
           try:
             self.ls4_ctrl = LS4_Control(ls4_conf=self.ls4_conf)
             self.logger = self.ls4_ctrl.ls4_logger
           except Exception as e:
             error_msg = "Exception instantiating ls4_ctrl: %s" % e
             self.logger.error(error_msg)

        if error_msg is None:
           self.logger.info("initializing ls4_ctrl")
           error_msg = await self.initialize()

               
        return error_msg

    async def close(self):

        """ put controller in auto-flush mode, close ls4_ctrl instance,
            and delete the instance
        """

        assert self.ls4_ctrl is not None, "ls4_ctrl is not instantiated"

        self.logger.info("closing controllers")
        error_msg = None

        self.logger.debug("unsyncing controllers")
        error_msg = await self.unsync()
        if error_msg:
          self.logger.error(error_msg)

        self.logger.debug("start autoflushing")
        try:
          await self.ls4_ctrl.start_flush()
        except Exception as e:
          error_msg = "Exception starting autoflush: %s" % e
          self.logger.error(error_msg)

        self.logger.debug("stopping controllers")
        try:
          await self.ls4_ctrl.stop()
        except Exception as e:
          error_msg = "Exception stopping controllers: %s" % e
          self.logger.error(error_msg)

        return error_msg


    async def run(self,ls4_conf=None):

      self.ls4_ctrl = None
      ls4_server = None
      server_status = None
      error_msg = None
      if self.logger is None:
        self.logger = LS4_Logger(name="LS4_CCP")
      self.ls4_conf = ls4_conf
      
      assert 'sync' in self.ls4_conf, "sync keyword missing from config"
      assert 'server_name' in self.ls4_conf, "server_name keyword missing from config"
      assert 'server_port' in self.ls4_conf, "server_port keyword missing from config"
      assert 'reset' in self.ls4_conf, "reset keyword missing from config"


      if self.ls4_conf['sync'] in ['TRUE','true','True',True]:
         self.sync_controllers = True
      else:
         self.sync_controllers = False

      if self.ls4_conf['reset'] in ['TRUE','true','True',True]:
         self.reset = True
      else:
         self.reset = False

      if self.reset:
         self.logger.warn("resetting controllers")

      self.logger.info("Initializing LS4_CPP")
      error_msg=await self.init()

      if error_msg is None:
        server_name=self.ls4_conf['server_name']
        server_port=self.ls4_conf['server_port']
        server_bufsize=1024
        self.logger.info("Instantiating LS4_Command_Server")

        async def command_fnc(command=None,command_args=None,reply_list=None):
           await self.command_function(command=command,command_args=command_args,reply_list=reply_list)

        try:
          ls4_server = LS4_Command_Server(host=server_name,port=server_port,\
                            maxbufsize=server_bufsize,\
                            command_fnc=command_fnc,logger=self.logger,\
                            command_dict=self.command_dict,error_reply=self.error_reply,done_reply=self.done_reply)
        except Exception as e:
          error_msg = "Exception instantiating command server: %s" % e
          self.logger.error(error_msg)


      if error_msg is None and not self.reset:
        self.logger.info("Running LS4_Command_Server")
        #DEBUG
        if 1:
        #try:
          await ls4_server.run()
        else:
        #except Exception as e:
          error_msg = "Exception running LS4_Command_Server: %s" % e
          self.logger.error(error_msg)


      if self.ls4_ctrl is not None:
        await self.close()

      self.logger.info("exiting" )

      if ls4_server is not None:
         server_status=ls4_server.server_status
      else:
         server_status={'error':True}

      return server_status,self.logger
   
if __name__ == "__main__":
   
  async def test():
      ls4_conf={}

      parser = argparse.ArgumentParser(description="LS4 camera control program")
      parser.add_argument('--ip_list', metavar='i', type=namelist, default='192.168.1.1,192.168.2.1,192.168.3.1,192.168.4.1',
                          help='list of controller IP addresses (cntrl 1 to 4)')
      parser.add_argument('--data_path', metavar='d', type=str, default='/data/ls4',
                          help='the path location for images and data')
      parser.add_argument('--conf_path', metavar='c', type=str, default='/home/ls4/archon/ls4_control/conf',
                          help='the path location for config files')
      parser.add_argument('--acf_list', metavar='a', type=namelist, \
                          default='test_nw.acf,test_sw.acf,test_se.acf,test_ne.acf',
                          help='the list of Archon config files (i.e. timing code)')
      parser.add_argument('--map_list', metavar='m', type=namelist, \
                          default='test_nw.json,test_sw.json,test_se.json,test_ne.json',
                          help='the list of ccd map files')
      parser.add_argument('--dark', metavar='D', type=str, default="False",
                          help='dark image if True')
      parser.add_argument('--exptime', metavar='e', type=float, default=0.0,
                          help='the image exposure time in sec')
      parser.add_argument('--init_count', metavar='N', type=int, default=0,
                          help='initial count of exposures already acquired')
      #parser.add_argument('--num_exp', metavar='n', type=int, default=1,
      #                    help='the number of exposures to take')
      parser.add_argument('--log_level', metavar='l', type=str, default='INFO',
                          help='the logging level(INFO, WARN, DEBUG, or ERROR)')
      parser.add_argument('--image_prefix', metavar='p', type=str, default='test',
                          help='the prefix for each image name')
      parser.add_argument('--leader', metavar='L', type=str, default='ctrl1',
                          help='the name of the lead controller')
      parser.add_argument('--sync', metavar='s', type=str, default="True",
                          help='sync controllers True or False')
      parser.add_argument('--test',  action='store_true',
                          help='test the controller')
      parser.add_argument('--save', metavar='S', type=str, default="True",
                          help='save images True or False')
      parser.add_argument('--fake', metavar='s', type=str, default="True",
                          help='fake controller True or False')
      parser.add_argument('--reset', metavar='R', type=str, default="False",
                          help='reset the controllers and exit')
      parser.add_argument('--ctrl_names', metavar='C', type=namelist, default=['ctrl1','ctrl2','ctrl3','ctrl4'],
                          help='names of controllers')
      parser.add_argument('--enable_list', metavar='E', type=namelist, default=['ctrl1','ctrl2','ctrl3','ctrl4'],
                          help='list of enabled controllers')
      parser.add_argument('--bind_list', metavar='b', type=namelist, default='192.168.1.10,192.168.2.10,192.168.3.10,192.168.4.10',
                          help='list of network ip address to bind controller connections ')
      parser.add_argument('--port_list', metavar='q', type=namelist, default='4242,4242,4242,4242',
                          help='list of network ports to bind controller connections ')
      parser.add_argument('--flush_time', metavar='c', type=float, default=30.0,
                          help='the time to initially flush the CCDs by continuously reading out')
      parser.add_argument('--power_down', type=str, default="True ",
                          help='power down on exir True or False')
      #parser.add_argument('--exp_incr', type=float, default=0.2,
      #                    help='the amount to increment the exposture time every other exposure')
      parser.add_argument('--server_name', metavar='H', type=str, default='ls4-workstn',
                          help='name of the command server host')
      parser.add_argument('--server_port', metavar='P', type=int, default=5000,
                          help='port number of the command server')

      abort = False # set to True if external abort triggered

      ls4_conf.update(vars(parser.parse_args()))
      ls4_ccp = LS4_CCP(ls4_conf=ls4_conf)

      error_msg = None
      logger=None

      done=False
      while not done:
          done=True
          status,logger=await ls4_ccp.run(ls4_conf)
          if status is None:
             logger.error("server status is None")
          elif 'restart' in status and status['restart']:
             logger.info("restart requested")
             done = False
          elif 'shutdown' in status and status['shutdown']:
             logger.info("shutdown requested")
          elif 'error' in status and status['error']:
             logger.info("error detected. shutting down")
            
  asyncio.run(test())
