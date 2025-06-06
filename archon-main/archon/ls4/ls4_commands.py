# LS4_Commnds class providing commands to be executed by LS4_CCP command server
#

import sys
import os
import asyncio
import time
import argparse
import json
from archon.ls4.ls4_control import LS4_Control
from archon.ls4.ls4_control import get_obsdate
from archon.ls4.ls4_abort import LS4_Abort
from archon.controller.ls4_logger import LS4_Logger
from archon.ls4.ls4_command_server import LS4_Command_Server
from archon.tools import check_bool_value
from archon.tools import get_obsdate

from . import DONE_REPLY,ERROR_REPLY,SHUTDOWN_COMMAND,RESTART_COMMAND,REBOOT_COMMAND


def get_arg_value(arg_name_list=None,arg_vals=None,arg_name=None):
  """ given a list of argument names (arg_name_list) and a corresponding list
      of arguments values (arg_vals), return the value for the
      named argument (arg_name)
  """
  assert arg_name in arg_name_list,\
      "argument %s does not appear in argument name list %s" %\
      (arg_name,str(arg_name_list))
  assert len(arg_name) ==  len(arg_vals),\
      "arg_name_list and arg_vals differ in length: %s %s" %\
      (arg_name_list,arg_vals)
  return arg_vals[arg_name_list.index(arg_name)]

class LS4_Commands():


    # commands understood by LS4_CCP
    # NOTE: make sure there are no spaced in the command names
    command_dict={\
        #'init':{'arg_name_list':[],'comment':'initialize camera controller'},\
        'open_shutter':{'arg_name_list':[],'comment':'open the camera shutter'},\
        'close_shutter':{'arg_name_list':[],'comment':'close the camera shutter'},\
        'status':{'arg_name_list':[],'comment':'return camera status'},\
        'expose':{'arg_name_list':['shutter','exptime','fileroot','exp_mode'],\
            'comment':'expose for exptime sec with shutter open (True,False) using exp_mode and saved to fileroot'},\
        'clear':{'arg_name_list':['clear_time'],'comment':'clear the camera for specified time'},\
        'erase':{'arg_name_list':[],'comment':'execute camera erase procedure'},\
        'purge':{'arg_name_list':['fast'],'comment':'run purge procedure with fast option (True,False)'},\
        'flush':{'arg_name_list':['fast','flushcount'],'comment':'execute flush procedure with fast option (True,Flase) and flushcount iterations (int)'},\
        'clean':{'arg_name_list':['erase','n_cycles','flushcount','fast'],'comment':'execute clean procedure with optional erase (True,False) for n_cycle interations (int) followed by a flush with fast (True/False) and flushcount(int) options'},\
        'vsub_on':{'arg_name_list':[],'comment':'enable Vsub bias. Bias power must be on already (see power_on)'},\
        'vsub_off':{'arg_name_list':[],'comment':'disable Vsub bias. Bias power must be on already (see power_on)'},\
        'power_on':{'arg_name_list':[],'comment':'turn on enabled bias voltages.'},\
        'power_off':{'arg_name_list':[],'comment':'turn off bias voltages. '},\
        'autoclear_on':{'arg_name_list':[],'comment':'turn on autoclearing when CCDs are idle.'},\
        'autoclear_off':{'arg_name_list':[],'comment':'turn off autoclearing.'},\
        'autoflush_on':{'arg_name_list':[],'comment':'turn on autoflushing when CCDs are idle.'},\
        'autoflush_off':{'arg_name_list':[],'comment':'turn off autoflushing.'},\
         #'r':{'arg_name_list':['num_lines','file_root'],\
         #    'comment':'readout num_lines from camera and write to file'},\
        'header':{'arg_name_list':['key_word','value'],\
             'comment':'add keyword/value to image fits header'},\
        'help':{'arg_name_list':[],'comment':'list commands and their args'}\
        }


    def __init__(self,ls4_control = None,ls4_abort=None):

       assert ls4_control is not None, "ls4_control is not instantiated"
       assert isinstance(ls4_control,(LS4_Control)),"ls4_control is not an instance of LS4_Control"
       assert ls4_abort is not None, "ls4_abort is not instantiated"
       assert isinstance(ls4_abort,(LS4_Abort)),"ls4_abort is not an instance of LS4_Abort"

       self.ls4_ctrl = ls4_control
       self.ls4_abort = ls4_abort

       self.ls4_conf = self.ls4_ctrl.ls4_conf
       self.logger=self.ls4_ctrl.ls4_logger
       self.info = self.logger.info
       self.debug= self.logger.debug
       self.warn = self.logger.warn
       self.error= self.logger.error
       self.critical= self.logger.critical

       self.done_reply = DONE_REPLY
       self.error_reply = ERROR_REPLY
       self.shutdown_command= SHUTDOWN_COMMAND
       self.restart_command = RESTART_COMMAND
       self.reboot_command = REBOOT_COMMAND


    async def command_function(self,command=None,arg_value_list=None,reply_list=None):

        error_msg = None
        reply_list[0]=self.done_reply
        arg_name_list=None
        arg_dict = None

        t_start = time.time()
        self.info("%s command [%s] args [%s]" %\
                     (get_obsdate(),command,str(arg_value_list)) )

        try:
          assert self.ls4_ctrl is not None, "ls4_ctrl is not instantiated"
          assert command is not None,"unspecified command"
          assert arg_value_list is not None,"unspecified arg_value_list"
          assert reply_list is not None,"unspecified reply_list"
          assert command in self.command_dict, "unrecognized command %s" % command
          arg_name_list = self.command_dict[command]['arg_name_list']
          assert arg_name_list is not None,"arg_name_list is None"
          assert len(arg_value_list)==len(arg_name_list),\
                    "lengths of arg_name_list[%s] and arg_value_list[%s] do not match" % \
                    (arg_name_list,arg_value_list)
        except Exception as e:
          error_msg = e

        # create dictionary linking arg names to arg values
        if error_msg is None:
           arg_dict = dict(zip(arg_name_list, arg_value_list))

        if error_msg is not None:
           pass

        elif command == 'open_shutter':
           self.info("opening shutter")
           await asyncio.sleep(2)

        elif command == 'close_shutter':
           self.info("closing shutter")
           await asyncio.sleep(2)

        elif command == 'status':
           await self.ls4_ctrl.update_cam_status()
           reply_list[0] = self.done_reply + " " + str(self.ls4_ctrl.status)
           reply_list[0] = reply_list[0].replace(",",",\n") 

        elif command == 'expose':
           self.info("awaiting expose with arg_dict : %s" % str(arg_dict))
           error_msg = await self.expose(arg_dict)
           self.info("done awaiting expose")
           if self.ls4_abort.abort:
             await self.ls4_abort.clear_exposure_abort()

        elif command == 'clear':
           error_msg = await self.clear(arg_dict)
           if self.ls4_abort.abort:
             await self.ls4_abort.clear_exposure_abort()

        elif command == 'clean':
           error_msg = await self.clean(arg_dict)

        elif command == 'erase':
           error_msg = await self.erase(arg_dict)

        elif command == 'purge':
           error_msg = await self.purge(arg_dict)

        elif command == 'flush':
           error_msg = await self.flush(arg_dict)

        elif command == 'vsub_on':
           error_msg = await self.enable_vsub()

        elif command == 'vsub_off':
           error_msg = await self.disable_vsub()

        elif command == 'power_on':
           error_msg = await self.power_on_biases()

        elif command == 'power_off':
           error_msg = await self.power_off_biases()

        elif command == 'autoclear_on':
           error_msg = await self.enable_autoclear()

        elif command == 'autoclear_off':
           error_msg = await self.disable_autoclear()

        elif command == 'autoflush_on':
           error_msg = await self.enable_autoflush()

        elif command == 'autoflush_off':
           error_msg = await self.disable_autoflush()


        #elif command == 'r':
        #   self.info("reading CCD images")
        #   await asyncio.sleep(2)

        elif command == 'header':
           self.info("modifying image header")
           extras = {arg_value_list[0]:arg_value_list[1]}
           error_msg = await self.ls4_ctrl.set_extra_header(extras)

        elif command == 'help':
           self.info("printing command help")
           reply_list[0] = self.done_reply + self.help_string()
           self.info("done printing command help")

        if error_msg is not None:
           self.error(error_msg)
           reply_list[0] = self.error_reply + " " + error_msg

        t_end = time.time()
        dt = t_end - t_start
        self.info("command done in %7.3f s" % dt)
        self.info("awaiting update_cam_status")
        await self.ls4_ctrl.update_cam_status()
        self.info("done awaiting update_cam_status")

        self.info("%s command [%s] args [%s] reply [%s]" %\
              (get_obsdate(),command,arg_value_list,reply_list[0]))
        self.info("done command function")

    def help_string(self,arg_dict=None):

        help_str="\n"
        for command in self.command_dict:
            c=self.command_dict[command]
            help_str += "%15s: " % command
            help_str += "args: %s\n" % (c['arg_name_list'])
            help_str += "%16s fnct: %s\n\n" % (" ",c['comment'])
 
        return help_str

    async def enable_vsub(self,arg_dict=None):
        """ enable Vsub bias. Bias Power must already be enabled """

        error_msg = None

        try:
          self.info("enabling Vsub bias")
          await self.ls4_ctrl.enable_vsub()
          self.info("done enabling Vsub bias")
        except Exception as e:
          error_msg = "Exception enabling Vsub bias: %s" %e

        return error_msg


    async def disable_vsub(self,arg_dict=None):
        """ disable Vsub bias. Bias Power must already be enabled """

        error_msg = None

        try:
          self.info("disabling Vsub bias")
          await self.ls4_ctrl.disable_vsub()
          self.info("done disabling Vsub bias")
        except Exception as e:
          error_msg = "Exception disabling Vsub bias: %s" %e

        return error_msg


    async def power_on_biases(self,arg_dict=None):
        """ power up CCD biases """

        error_msg = None

        try:
          self.info("powering up biases")
          await self.ls4_ctrl.power_up_biases()
          self.info("done powering up biases")
        except Exception as e:
          error_msg = "Exception powering up CCD biases: %s" %e

        return error_msg


    async def power_off_biases(self,arg_dict=None):
        """ power down CCD biases """

        error_msg = None

        try:
          self.info("powering down biases")
          await self.ls4_ctrl.power_down_biases()
          self.info("done powering down biases")
        except Exception as e:
          error_msg = "Exception powering down CCD biases: %s" %e

        return error_msg

    async def enable_autoclear(self,arg_dict=None):
        """ enable autoclearing of CCDs when idle """

        error_msg = None

        try:
          self.info("enabling autoclear")
          await self.ls4_ctrl.enable_autoclear()
          self.info("done enabling autoclear")
        except Exception as e:
          error_msg = "Exception enabling autoclear: %s" %e

        return error_msg


    async def disable_autoclear(self,arg_dict=None):
        """ disable autoclearing of CCDs when idle """

        error_msg = None

        try:
          self.info("disabling autoclear")
          await self.ls4_ctrl.disable_autoclear()
          self.info("done disabling autoclear")
        except Exception as e:
          error_msg = "Exception disabling autoclear: %s" %e

        return error_msg


    async def enable_autoflush(self,arg_dict=None):
        """ enable autoflushing of CCDs when idle """

        error_msg = None

        try:
          self.info("enabling autoflush")
          await self.ls4_ctrl.enable_autoflush()
          self.info("done enabling autoflush")
        except Exception as e:
          error_msg = "Exception enabling autoflush: %s" %e

        return error_msg


    async def disable_autoflush(self,arg_dict=None):
        """ disable autoflushing of CCDs when idle """

        error_msg = None

        try:
          self.info("disabling autoflush")
          await self.ls4_ctrl.disable_autoflush()
          self.info("done disabling autoflush")
        except Exception as e:
          error_msg = "Exception disabling autoflush: %s" %e

        return error_msg

    async def clear(self,arg_dict=None):
        """ continuously read out ccds for clear_time sec.
            THe clear can be terminated using the 'abort_exposure' script
        """

        error_msg = None
        try:
          clear_time = float(arg_dict['clear_time'])
        except Exception as e:
          error_msg = "Exception parsing args for clear command: %s" % e

        if error_msg is None:
          try:
            self.info("clearing: %s" % arg_dict)
            await self.ls4_ctrl.clear(clear_time=clear_time)
            self.info("done clearing: %s" % arg_dict)
          except Exception as e:
            error_msg = "Exception clearing %s: %s" % (arg_dict,e)

        return error_msg


    async def erase(self,arg_dict=None):
        """ run erase procedure on CCDs """

        error_msg = None

        try:
          self.info("erasing")
          await self.ls4_ctrl.erase()
          self.info("done erasing")

        except Exception as e:
          error_msg = "Exception erasing: %s" % e

        return error_msg


    async def purge(self,arg_dict=None):
        """ run purge procedure on CCDs """

        error_msg = None
        arg_name_list=None
        try:
          fast = arg_dict['fast']
          fast = check_bool_value(fast,True)
        except Exception as e:
          error_msg = "Exception parsing args for purge command: %s" % e

        if error_msg is None:
          try:
            self.info("purging: %s" % arg_dict)
            await self.ls4_ctrl.purge(fast=fast)
            self.info("done purging: %s" % arg_dict)
          except Exception as e:
            error_msg = "Exception purging %s: %s" % (arg_dict,e)

        return error_msg

    async def flush(self,arg_dict=None):
        """ run flush procedure on CCDs """

        error_msg = None
        arg_name_list=None
        try:
          fast = arg_dict['fast']
          fast = check_bool_value(fast,True)
          flushcount= arg_dict['flushcount']
          flushcount = int(flushcount)
        except Exception as e:
          error_msg = "Exception parsing args for flush command: %s" % e

        if error_msg is None:
          try:
            self.info("flushing: %s" % arg_dict)
            await self.ls4_ctrl.flush(fast=fast,flushcount=flushcount)
            self.info("done flushing: %s" % arg_dict)
          except Exception as e:
            error_msg = "Exception flushing %s: %s" % (arg_dict,e)

        return error_msg

    async def clean(self,arg_dict=None):
        """ run cleaning procedure on CCDs """

        error_msg = None
        arg_name_list=None
        try:
          fast = arg_dict['fast']
          fast = check_bool_value(fast,True)
          flushcount= int(arg_dict['flushcount'])
          erase = arg_dict['erase']
          erase = check_bool_value(erase,True)
          n_cycles= int(arg_dict['n_cycles'])
        except Exception as e:
          error_msg = "Exception parsing args for clean command: %s" % e
        if error_msg is None:
          try:
            self.info("cleaning: %s" % arg_dict)
            await self.ls4_ctrl.clean(erase=erase,n_cycles=n_cycles,fast=fast,flushcount=flushcount)
            self.info("done cleaning: %s" % arg_dict)
          except Exception as e:
            error_msg = "Exception cleaning %s: %s" % (arg_dict,e)

        if error_msg is not None:
           self.error(error_msg)
        return error_msg


    async def expose(self,arg_dict=None):

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
        #
        # exposures can be aborted using the "abort_exposure" script.

        error_msg = None
        arg_name_list = None

        save = self.ls4_conf['save'] # must be True to save exposures to disk

        try:
          shutter = arg_dict['shutter']
          shutter = check_bool_value(shutter,True)
          exptime = float(arg_dict['exptime'])
          fileroot= arg_dict['fileroot']
          exp_mode= arg_dict['exp_mode']
          exp_num = self.ls4_ctrl.image_count
        except Exception as e:
          error_msg = "Exception parsing args : %s" % e


        if error_msg is None:
          try:
            self.info("exposing : %s" % arg_dict)
            error_msg = await self.ls4_ctrl.expose(exptime=exptime,exp_num=exp_num,
                    exp_mode = exp_mode, enable_shutter=shutter, fileroot=fileroot)
            self.info("done exposing : %s" % arg_dict)

          except Exception as e:
            error_msg = "Exception exposing %s: %s" % (arg_dict,e)

        return error_msg
