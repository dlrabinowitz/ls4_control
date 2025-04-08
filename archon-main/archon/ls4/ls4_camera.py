############################
# -*- coding: utf-8 -*-
#
# @Author: David Rabinowitz (david.rabinowitz@yale.edu)
# @Date: 2024-01-16
# @Filename: ls4_camera.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)
#
# Python code defining LS4_Camera class 
# The LS4 camera-control program instantiated one
# instance of the class for each Archon controller.
# All access to the controller (initializing, 
# configuring, exposing, readout, buffer access)
# is through this class.
#
# The class is an extensionn of the sdss-archon code
# available on github. Some of the sdss-archon code was
# modified for this purpose
#
################################

import numpy as np
import sys
import asyncio
import archon
#from archon import log
#import logging
from archon.controller.ls4_logger import LS4_Logger
from archon.controller.ls4_controller import LS4Controller
from archon.controller.ls4_controller import TimePeriod
from archon.controller.maskbits import ArchonPower
from archon.ls4.ls4_sync import LS4_Sync
from archon.ls4.ls4_voltages import LS4_Voltages 
from astropy.io import fits
import json
import time
import argparse
#from . import MAX_COMMAND_ID,FOLLOWER_TIMEOUT_MSEC
from . import VOLTAGE_TOLERANCE, MAX_FETCH_TIME, AMPS_PER_CCD, MAX_CCDS, VSUB_BIAS_NAME
from archon.tools import get_obsdate
from typing import Any, Callable, Iterable, Literal, Optional, cast, overload

# Notes about LS4 tap lines and CCD placement
#
# For each quadrant of the CCD (NW, NE, SW, SE) there are 8 connectors (A, B, ..., H)
# on the mother board, one for each CCD location in the focal plane:
#
#         __________________NORTH__________________
#       |                     |                     |
#       | NW-A NW-B NW-C NW-D | NE-E NE-F NE-G NE-H |
#       |                     |                     |
#       |                     |                     |
#       |                     |                     |
#       | NW-E NW-F NW-G NW-H | NE-A NE-B NE-C NE-D |
#       |                     |                     |
#  WEST | ____________________|_____________________| EAST
#       |                     |                     |
#       |                     |                     |
#       | SW-A SW-B SW-C SW-D | SE-E SE-F SE-G SE-H |
#       |                     |                     |
#       |                     |                     |
#       |                     |                     |
#       | SW-E SW-F SW-G SW-H | SE-A SE-B SE-C SE-D |
#       |                     |                     |
#       | __________________SOUTH___________________|
#
#
# The controller reads out each CCD by two video amplifier outputs or "taps". These
# two outputs read out the "left" and "right" halves of the CCD, respectively.
# and max 8 CCDs. However, the controller can be configured only a subset of the tap.
#
# The taps are numbered 1 to 16, and are assigned a direction for storing the images
# pixels into the frame buffer ("L" or "R"). This preserves the relative pixel orientation
# in the data buffer. The connection in the mother board are assigned taps, as follows:
#
# motherboard controller taps
# location    (left, right)
# A           AD3L,  AD4R
# B           AD2L,  AD1R
# C           AD8L,  AD7R
# D           AD6L,  AD5R
# E           AD12L, AD11R
# F           AD10L, AD9R
# G           AD13L, AD14R
# H           AD15L, AD16R
#
#
# In the controller config file ("*.acf"), the order in which the CCD taps are
# readout into the image buffer is decribed by "TAPLINE0", "TAPLINE1", ...,
# "TAPLINEN", where N is the number of taps that are read out (can be 1 to 16).
# The number of taps read out is specified by "TAPLINES"
# Here is an example:
#  TAPLINE0="AD3L, 1, 4900"
#  TAPLINE1="AD4R, 1, 1000"
#  TAPLINE2="AD12L, 1, 5000"
#  TAPLINE3="AD11R, 1, 700"
#  TAPLINE4=
#  TAPLINES=4
#
#  To provide additional information about CCD locations to the controller, an optional
#  "ccd_map" may be provided. For example, if only location "A" and "E" are occupied :
#
#     ccd_map =  {"A":{"CCD_NAME":"S-003"},
#                 "E":{"CCD_NAME":"S-196"}}
#
#  In this test program, the ccd_map provided in the format of a json-encoded text file:
#  E.G:
#  {"A": {"CCD_NAME": "S-003"}, "E": {"CCD_NAME": "S-196"}}
#

class LS4_Camera():

    # There are 8 CCD locations per controller ("A",...,"H"). 
    # There are two amps per CCD ("LEFT" and "RIGHT")
    # Each tap name corresponds to one of the amps at one of the CCD locations

    # static map from tap name to ccd and amp location
    tap_locations={"AD3":{"LOCATION":"A","AMP_NAME":"LEFT"}, "AD4":{"LOCATION":"A","AMP_NAME":"RIGHT"},
                   "AD2":{"LOCATION":"B","AMP_NAME":"LEFT"},"AD1":{"LOCATION":"B","AMP_NAME":"RIGHT"},
                   "AD8":{"LOCATION":"C","AMP_NAME":"LEFT"}, "AD7":{"LOCATION":"C","AMP_NAME":"RIGHT"},
                   "AD6":{"LOCATION":"D","AMP_NAME":"LEFT"}, "AD5":{"LOCATION":"D","AMP_NAME":"RIGHT"},
                   "AD12":{"LOCATION":"E","AMP_NAME":"LEFT"}, "AD11":{"LOCATION":"E","AMP_NAME":"RIGHT"},
                   "AD10":{"LOCATION":"F","AMP_NAME":"LEFT"}, "AD9":{"LOCATION":"F","AMP_NAME":"RIGHT"},
                   "AD13":{"LOCATION":"G","AMP_NAME":"LEFT"}, "AD14":{"LOCATION":"G","AMP_NAME":"RIGHT"},
                   "AD15":{"LOCATION":"H","AMP_NAME":"LEFT"}, "AD16":{"LOCATION":"H","AMP_NAME":"RIGHT"}}

    # static map from ccd location to tap names for each amp
    tap_names={"A":{"LEFT":"AD3","RIGHT":"AD4"},
               "B":{"LEFT":"AD2","RIGHT":"AD1"},
               "C":{"LEFT":"AD8","RIGHT":"AD7"},
               "D":{"LEFT":"AD6","RIGHT":"AD5"},
               "E":{"LEFT":"AD12","RIGHT":"AD11"},
               "F":{"LEFT":"AD10","RIGHT":"AD9"},
               "G":{"LEFT":"AD13","RIGHT":"AD14"},
               "H":{"LEFT":"AD15","RIGHT":"AD16"}}

    amps_per_ccd = AMPS_PER_CCD
    max_ccds = 8
    max_taps = amps_per_ccd * max_ccds

    required_conf_params = ['data_path','acf_file','test','log_level','ip','name']
    default_params = {'data_path':'/tmp','test':False,'log_level':'INFO','ip':'10.0.0.2','name':'ctrlx','local_addr':('127.0.0.1',4242)}

    def __init__(self,
        ls4_conf: dict | None = None,
        ls4_sync: LS4_Sync | None = None,
        param_args: list[dict] | None = None,
        command_args: list[dict] | None = None,
        fake: bool | None = None,
    ):
       
        """ ls4_conf is a dictionary with configuration variables for the instance of LS4_Camera.
       
            ls4_sync is a class to handle synchronizing camera threads

            param_args is a list with one entry -- a dictionary to hold parameter arguments 
            for sync_set_param. It is set up as a list so that any changes to the dictionary
            contents are inherited by all threads sharing param_args. 

            command_args is  also a list with one entry -- a dictionary to hold command arguments 
            for sync_send_command. It is set up as a list so that any changes to the dictionary
            contents are inherited by all threads sharing command_args
        """

        self.ls4_controller = None
        self.ls4_voltages = None
        self.ls4_sync = None
        self.ls4_logger = None
        self.check_voltages=None

        self.leader = False
        if fake is not None:
          self.fake_controller = fake
        else:
          self.fake_controller = False

        self.prefix = ""

        assert ls4_conf is not None,"unspecified ls4 configuration"
        assert ls4_sync is not None,"unspecified ls4 sync operators"
        assert param_args is not None,"unspecified param_args"
        assert command_args is not None,"unspecified command_args"
        assert len(param_args)==1, "param_args is not a list of length 1"
        assert len(command_args)==1, "command_args is not a list of length 1"

        self.ls4_sync = ls4_sync

        for key in self.default_params:
            if key not in ls4_conf:
               ls4_conf[key]=self.default_params[key]

        for param in self.required_conf_params:
            assert param in ls4_conf, \
                    "parameter [%s] must be specified in configuration options [%s]" % (param,ls4_conf)
            assert ls4_conf[param] is not None,\
                    "configuration parameter [%s] can not be None" % param
            assert ls4_conf[param] not in ["","None","NONE","none"], \
                    "configuration parameter [%s] can not be [%s]" % (param,ls4_conf[param])

        self.data_path =  ls4_conf['data_path']
        self.ip_address = ls4_conf['ip']
        self.local_addr = ls4_conf['local_addr']
        self.name = ls4_conf['name']
        self.index = ls4_conf['index']

        self.ls4_logger = LS4_Logger(leader=self.leader,name=self.name)
        self.info = self.ls4_logger.info
        self.debug= self.ls4_logger.debug
        self.warn = self.ls4_logger.warn
        self.error= self.ls4_logger.error
        self.critical= self.ls4_logger.critical

        if 'log_format' in ls4_conf and ls4_conf['log_format'] is not None:
          self.debug("setting log format to %s" % ls4_conf['log_format'])
          self.ls4_logger.set_format(ls4_conf['log_format'])

        self.ls4_logger.set_level(ls4_conf['log_level'])

        self.ls4_test = ls4_conf['test']

        # LS4 instance of LS4Controller
        self.ls4_controller = None

        # fetched image-data buffer
        self.image_data=None

        # text file used to configure archon controller
        self.acf_conf_file = ls4_conf['acf_file']

        # dictionary to be parsed from acf_conf_file by LS4Controller
        self.acf_conf = None

        # filled in by update_ccd_map()
        self.image_info={}

        # to be initialized by load_ccd_map()
        self.ccd_map=None

        if 'map_file' in ls4_conf:
          self.debug("loading ccd map file %s" % ls4_conf['map_file'])
          try: 
             self.load_ccd_map(ccd_map_file=ls4_conf['map_file'], upper_flag=True)
          except Exception as e:
             raise RuntimeError("unable to load ccd_map_file %s" % ls4_conf['map_file'])

    
        self.ls4_conf = ls4_conf
 
        # self.param_args[0] is a shared global
        self.param_args = param_args

        # self.command_args[0] is a shared global
        self.command_args = command_args

        #initialize timers
        self.timing={'expose':TimePeriod(),
                     'readout':TimePeriod(),
                     'fetch': TimePeriod(),
                     'save': TimePeriod()}
 
        # copies of ls4_controller config, device status and system
        # status to be used for header parameters each time an
        # image is fetched from the controller. THis may occur at the
        # same time as a new image is exposed and readout, where the
        # the current values for these parameters are updated.
        self.fetch_ls4_conf={}
        self.fetch_config={}
        self.fetch_status={}
        self.fetch_system={}

    def set_lead(self, lead_flag: bool = False):
        self.leader = lead_flag
        self.prefix = "leader %s:" % self.name
        self.ls4_logger.leader=lead_flag
        if self.ls4_controller is not None:
           self.ls4_controller.set_lead(lead_flag)

    def update_conf(self,keyword=None,val=None):
        self.ls4_conf.update({keyword:val})

    def load_ccd_map(self,ccd_map_file=None,upper_flag=False):

        """ load contents of json-formatted file(ccd_map_file) in self.ccd_map.
            if upper_flag = True, convert all text in file to upper case before loading.
        """

        assert ccd_map_file is not None, "unspecified ccd_map_file"

        try:
          fin = open(ccd_map_file,"r")
        except Exception as e:
          self.error("exception opening ccd_map_file %s: %s" % (ccd_map_file,e))
          raise RuntimerError(e)

        try:
          content = fin.read()
          fin.close()
          if upper_flag:
             content = content.upper()
          self.ccd_map=json.loads(content)
        except Exception as e:
          self.error("exception loading ccd_map from ccd_map_file %s: %s" % (ccd_map_file,e))
          raise RuntimerError(e)


    def notifier(self,str):
        self.debug(str)

    async def get_status(self):
        status = None
        try:
          status = await self.ls4_controller.get_device_status()
        except Exception as e:
          self.error("exception getting device status: %s" %e)
          return None

        return status

    async def get_system(self):
        system = None
        try:
          system = await self.ls4_controller.get_system()
        except Exception as e:
          self.error("exception getting device system: %s" %e)
          return None

        return system


    async def power_up(self):
        """ power down CCD biases """
        result = None

        power_state = await self.ls4_controller.power()
        self.info("Power state before powering up: %s" % power_state)

        try:
          result = await self.ls4_controller.power(mode=True)
        except Exception as e:
          self.error("exception powering up controller biases: %s" %e)

        await asyncio.sleep(2)

        power_state = await self.ls4_controller.power()
        self.info("Power state after  powering up: %s" % power_state)

        status = await self.get_status()
        assert await self.check_voltages(status=status), "voltages out of range" 
        return result

    async def power_down(self):
        """ power up CCD biases """
        result = None
    
        power_state = await self.ls4_controller.power()
        self.info("Power state before powering down: %s" % power_state)

        try:
          result = await self.ls4_controller.power(mode=False)
        except Exception as e:
          self.error("exception powering down controller biases: %s" %e)

        await asyncio.sleep(2)

        power_state = await self.ls4_controller.power()
        self.info("Power state after powering down: %s" % power_state)
        return result

    async def enable_vsub(self):
        """ enable Vsub bias. Return None on success, error_msg on failure  """

        bias_status=None
        error_msg = None
        try:
          self.debug("calling ls4_controller.enable_vsub")
          error_msg = await self.ls4_controller.enable_vsub()
          self.debug("done calling ls4_controller.enable_vsub")
          self.debug("error_msg is %s" % error_msg)
        except Exception as e:
          error_msg ="exception enabling Vsub bias: %s" % e

        if error_msg is None:
          try:
            status = await self.get_status()
            bias_status = await self.check_voltages(status=status,bias_name=VSUB_BIAS_NAME)
            if bias_status is None:
               error_msg = "failed to get Vsub bias status"
          except Exception as e:
            error_msg ="exception checking Vsub bias: %s" % e

        if error_msg is None:
          if not bias_status['enabled']:
             error_msg = "failed to enable Vsub bias"
          elif not bias_status['ok']:
             error_msg = "Vsub enabled but not in tolerance: set %7.3f  meas: %7.3f" %\
                          (bias_status['v_set'],bias_status['v_meas'])

        if error_msg is not None:
          self.error(error_msg)
        return error_msg


    async def disable_vsub(self):
        """ disable Vsub bias. Return None on success, error_msg on failure  """

        bias_status=None
        error_msg = None
        try:
          error_msg = await self.ls4_controller.disable_vsub()
        except Exception as e:
          error_msg ="exception disabling Vsub bias: %s" % e

        if error_msg is None:
          try:
            status = await self.get_status()
            bias_status = await self.check_voltages(status=status,bias_name=VSUB_BIAS_NAME)
            if bias_status is None:
               error_msg = "failed to get Vsub bias status"
          except Exception as e:
            error_msg ="exception checking Vsub bias: %s" % e

        if error_msg is None:
          if bias_status['enabled']:
             error_msg = "failed to disable Vsub bias"
          elif not bias_status['ok']:
             error_msg = "Vsub disabled but still in tolerance: set %7.3f  meas: %7.3f" %\
                          (bias_status['v_set'],bias_status['v_meas'])
          elif bias_status['v_meas']>3.0:
             error_msg = "Vsub disabled but still high: %7.3f" %\
                          bias_status['v_meas']

        if error_msg is not None:
          self.error(error_msg)

        return error_msg

    async def start_autoclear(self):

        error_msg = None
        try:
          self.debug("starting autoclear")
          error_msg = await self.ls4_controller.set_autoclear(mode=True)
          self.debug("done starting autoclear")
        except Exception as e:
          error_msg="exception starting autoclear: %s" %e
          self.error(error_msg)

        return error_msg
          
    async def stop_autoclear(self):

        error_msg=None
        try:
          self.debug("stopping autoclear")
          error_msg = await self.ls4_controller.set_autoclear(mode=False)
          self.debug("done stopping autoclear")
        except Exception as e:
          error_msg="exception stopping autoclear %s: " %e
          self.error(error_msg)
        return error_msg


    async def start_autoflush(self):

        error_msg = None
        try:
          self.debug("starting autoflush")
          error_msg = await self.ls4_controller.set_autoflush(mode=True)
          self.debug("done starting autoflush")
        except Exception as e:
          error_msg="exception starting autoflush: %s" %e
          self.error(error_msg)

        return error_msg
          
    async def stop_autoflush(self):

        error_msg=None
        try:
          self.debug("stopping autoflush")
          error_msg = await self.ls4_controller.set_autoflush(mode=False)
          self.debug("done stopping autoflush")
        except Exception as e:
          error_msg="exception stopping autoflush %s: " %e
          self.error(error_msg)
        return error_msg

    async def erase(self):
        """ execute CCD erase procedure """

        error_msg=None
        try:
          self.debug("start erasing")
          error_msg = await self.ls4_controller.erase()
          self.debug("done erasing")
        except Exception as e:
          error_msg = "exception executing CCD erase procedure: %s" %e
          self.error(error_msg)
        return error_msg
          
    async def purge(self,fast=False):
        """ execute CCD purge procedure """

        error_msg = None
        try:
          self.debug("running CCD purge with fast =  %s" % fast)
          error_msg = await self.ls4_controller.purge(fast=fast)
          self.debug("done running CCD purge with fast =  %s" % fast)
        except Exception as e:
          error_msg = "exception excuting CCD purge procedure with fast = %s: %s" % (fast,e)
          self.error(error_msg)
        return error_msg

    async def flush(self,fast=False,flushcount=1):
        """ execute CCD flush procedure """

        error_msg=None
        try:
          self.debug("start flushing with fast=%s and flushcount=%d" % (fast,flushcount))
          error_msg = await self.ls4_controller.flush(fast=fast,flushcount=flushcount)
          self.debug("done flushing with fast=%s and flushcount=%d" % (fast,flushcount))
        except Exception as e:
          error_msg="exception flushing with fast=%s and flushcount=%d: %s" % (fast,flushcount,e)
          self.error(error_msg)
        return error_msg

    async def clean(self,erase=False, n_cycles=10, flushcount=3,fast = False):
        """ execute CCD clean procedure with the specified options  """
       
        error_msg=None
        try:
          self.debug("running cleaning procedure with erase,n_cycles,flushcount,fast = %s %d %d %s" %\
                 (erase,n_cycles,flushcount,fast))
          error_msg = await self.ls4_controller.clean(erase=erase,n_cycles=n_cycles,flushcount=flushcount, fast=fast)
          self.debug("done running cleaning procedure with erase,n_cycles,flushcount,fast = %s %d %d %s" %\
                 (erase,n_cycles,flushcount,fast))
        except Exception as e:
          error_msg = "exception running cleaning procedure with erase,n_cycles,flushcount,fast = %s %d %d %s : %s" %\
                 (erase,n_cycles,flushcount,fast,e)
          self.error(error_msg)
        return error_msg

    async def abort_exposure(self,readout=True):
        """ abort ongoing exposure and readout if readout is True """

        error_msg=None
        try:
            self.debug("aborting ongoing exposure with readout = %s" % readout)
            error_msg = await self.ls4_controller.abort(readout=readout)
            self.debug("done aborting ongoing exposure with readout = %s" % readout)
        except Exception as e:
            error_msg = "exception aborting ongoing exposure with readout %s: %s" % (readout,e)
            self.error(error_msg)

        return error_msg

    async def init_controller(self,hold_timing=False,reboot=False):
        """ if hold_timing is True, set the controller state to hold off executing the timing
            script when the config file is loaded by start_controller().
            If reboot is True, reboot the controllers before initializing.
        """
 
        self.debug("initializing controller with reboot = %s" % reboot)

        error_msg = None
        cmd = None

        try:
          assert self.ls4_controller == None,"controller already started"
        except Exception as e:
          error_msg = "%s" % e

        if error_msg is None:
          try: 
            self.ls4_controller = LS4Controller(name=self.name,
                 host=self.ip_address,local_addr=self.local_addr,
                 param_args=self.param_args,command_args=self.command_args,
                 ls4_events = self.ls4_sync.ls4_events,
                 ls4_logger=self.ls4_logger,
                 fake=self.fake_controller,
                 timing=self.timing,
                 reboot=reboot,
                 idle_function =  self.ls4_conf['idle_function'],
                 acf_file = self.acf_conf_file,
                 notifier=self.notifier,
                 index=self.index)
            self.debug("awaiting ac.start")
            await self.ls4_controller.start(reset=False)
          except Exception as e:
            error_msg = "exception starting archon controller: %s" % e

        if error_msg is None:
           try:
              self.ls4_voltages = LS4_Voltages(ls4_controller = self.ls4_controller, logger = self.ls4_logger)
              self.check_voltages = self.ls4_voltages.check_voltages
           except Exception as e:
              error_msg = "exception instantiating LS4_Voltages: %s" % e

        if error_msg is None and hold_timing is True:
          try:
            self.debug("hold timing until after config file is loaded")
            await self.hold_timing()
          except Exception as e:
            error_msg = "exception holding timing for archon controller: %s" % e

        if error_msg:
            self.error(error_msg)
            raise RuntimeError(error_msg)
        else:
            self.debug("controller initialized")

    async def reset(self,release_timing=False):

        error_msg = None

        try:
          assert self.ls4_controller != None,"controller must first be initialized"
        except Exception as e:
          error_msg = "%s" % e

        if error_msg is None:
          try:
            await self.ls4_controller.reset(release_timing=release_timing)
          except Exception as e:
            error_msg = "exception resetting controller: %s" % e


    async def hold_timing(self):

        error_msg = None

        try:
          assert self.ls4_controller != None,"controller must first be initialized"
        except Exception as e:
          error_msg = "%s" % e

        if error_msg is None:
          try:
            await self.ls4_controller.hold_timing()
          except Exception as e:
            error_msg = "exception holding timing for controller: %s" % e

    async def release_timing(self):

        error_msg = None

        try:
          assert self.ls4_controller != None,"controller must first be initialized"
        except Exception as e:
          error_msg = "%s" % e

        if error_msg is None:
          try:
            await self.ls4_controller.release_timing()
          except Exception as e:
            error_msg = "exception releasing timing for controller: %s" % e

    async def start_controller(self,release_timing=True,power_on=True):
        """ 

            Write the timing code and configuration data from the Archon Config File to
            the controller and optionally power on.

            If release_timing is False, the controller will not start its timing scripts until
            self.ls4_controller.release_timing() is later executed. This synchronizes
            the timing scripts for controller connected by sync cables

            If power_on is True, power up the biases to the CCDs after configuring the controller.

        """
            
        error_msg = None
        cmd = None

        try:
          assert self.ls4_controller != None,"controller must first be initialized"
        except Exception as e:
          error_msg = "%s" % e

        if error_msg is None  and  self.acf_conf_file is not None:
          self.debug("writing acf_conf_file %s to controller, release_timing is %s" %\
                      (self.acf_conf_file,release_timing))
          try:
            # in test mode, do apply configuration to controller and do not power it on
            if self.ls4_test:
              await self.ls4_controller.write_config(release_timing=release_timing,
                             input=self.acf_conf_file,\
                             applyall=False,poweron=False)
            else:
              await self.ls4_controller.write_config(release_timing=release_timing,\
                             input=self.acf_conf_file,\
                             applyall=True,poweron=power_on)
            self.debug("done writing acf_conf_file %s to controller, release_timing is %s" %\
                      (self.acf_conf_file,release_timing))
          except Exception as e:
            error_msg = "exception writing acf_conf_file to controller: %s" % e


        if power_on and error_msg is None:
           try:
              status = await self.get_status()
              assert await self.check_voltages(status=status), "voltages out of range"
           except Exception as e:
              error_msg = e
 
        if error_msg is None:
          self.acf_conf=self.ls4_controller.acf_config
          try:
            self._update_ccd_map()
          except Exception as e:
            error_msg="exception updating ccd_map: %s" % e

        if error_msg:
            self.error(str(error_msg))
            raise RuntimeError(error_msg)
        else:
            self.info("controller started sucessfully")

    async def stop_controller(self,power_down=True):

        power_state = None

        assert self.ls4_controller is not None,"ERROR: controller has not been started"

        if power_down:
          try:
            self.info("powering down controller")
            power_state = await self.power_down()
            self.info("power state is %s" % power_state)
          except Exception as e:
            self.error("exception powering down controller: %s" %e)

          if (power_state != ArchonPower.OFF):
               self.error("unable to power down controller")
         
        try:
          self.info("stopping controller")
          await self.ls4_controller.stop()
        except Exception as e:
          self.error("exception stopping controller: %s" % e)

        self.ls4_controller = None 

    async def save_image(self,output_image=None, status=None, controller_config = None, system=None, ls4_conf = None):

        self.timing['save'].start()

        if status is None:
          status=self.fetch_status
        if system is None:
          system= self.fetch_system
        if controller_config is None:
          config = self.fetch_config
        if ls4_conf is None:
          ls4_conf = self.fetch_ls4_conf

        image_index = 0
        header_info0 = {}
        header_info0 = self._get_header_info(header_info0,conf = ls4_conf)
        header_info0 = self._get_header_info(header_info0,conf = config['expose_params'])
        header_info0 = self._get_header_info(header_info0,conf = config['archon'])
        header_info0 = self._get_header_info(header_info0,conf = status)
        header_info0 = self._get_header_info(header_info0,conf = system)


        for ccd_location in self.ccd_map:
          for amp_index in range(0,self.amps_per_ccd):
            amp_selection = self._get_amp_selection(amp_index)
            if amp_selection is not None:
                ccd_data_list = self._get_ccd_data(ccd_location=ccd_location,amp_selection=amp_selection)
                ccd_data = ccd_data_list[0]
                image_name =  output_image.replace(".fits","")
                image_name = image_name + "_%02d"%image_index + ".fits"

                header_info = {}
                header_info.update(header_info0)
                header_info = self._get_header_info(header_info,ccd_location=ccd_location,\
                      amp_index = amp_index)

                hdu = fits.PrimaryHDU(ccd_data)
                header = hdu.header
                for k in header_info:
                  key = k
                  if len(key.rstrip())>8:
                     key = "HIERARCH "+ key
                 
                  if isinstance(header_info[k],(float,)) and k in ["actexpt","read_per"]:
                     header_info[k] = round(header_info[k],3)
                  header[key] = header_info[k]

                hdul = fits.HDUList([hdu])
                hdul.writeto(image_name,overwrite=True)
                hdul.close()
                try:
                  del hdu
                except:
                  pass
                image_index += 1

        self.timing['save'].end()
    
    async def acquire(
        self,
        output_image: str | None = None,
        exptime: float = 0.0,
        acquire: bool = True,
        fetch: bool = True,
        concurrent: bool = False,
        save: bool = True,
        enable_shutter: bool =True,
        exp_done_callback: Optional[Callable[[str,int], None]] = None, 

    ) -> None:

        """  If acquire = True: acquire a new  exposure and readout to controller memory.

             If fetch = True:  fetch the data from controller memory and write to disk (if save =True)

             IF acquire/fetch = False/True : fetch previously acquired data from controller memory

             If acquire/fetch= True/Fase: acquire a new exposure and save to controller memory only

             If enable_shutter = True/False: enable/disable shutter during exposure

             If concurrent = True, don't fetch until any concurrent exposure (running in a separate
             thread) has starting exposing, or else started reading out (depending on exposure time).

             Note: Can not have acquire=fetch=concurrent=True. This is because concurrent
             fetching can only occur in a thread where acquire = False.
        """

        error_msg = None
        cmd = None
        self.image_data = None

        assert acquire or fetch, "acquire or fetch must be true"
        if concurrent:
           assert not (acquire and fetch),\
               "can not have concurrent=True if both fetch and acquire are True"

        self.debug("acquire with output/exptime/acquire/fetch/concurrent/save/shutter :\
                  %s/ %7.3f/ %s/ %s/ %s/ %s/ %s" %\
                  (output_image,exptime,acquire,fetch,concurrent,save,enable_shutter))


        try:
           assert self.ls4_controller is not None,"controller has not been started"
        except Exception as e:
           error_msg = e

        if error_msg is None:
          status = await self.get_status()
          system = await self.get_system()


        if error_msg is None:

          if not acquire:
             self.debug("skipping acquisition of new image")
          else:

            # save the status before starting next exposure. Thus info will
            # be used to decide which controller buffer to fetch data from and
            # which status to save to the image header
            self.fetch_status.update(status)
            try:
              assert await self.check_voltages(status),"voltages out of range first check"
            except Exception as e:
              error_msg = e

            if error_msg is None:
              pass
              #print ("erasing")
              #await ls4.ls4_controller.erase()
              #print ("purging")
              #await ls4.ls4_controller.purge(fast=True)
              #print ("cleaning")
              #await ls4.ls4_controller.cleanup(n_cycles=1)

            if error_msg is None:
              self.debug("start exposing %7.3f sec." % exptime)
              try:
                self.ls4_controller.shutter_enable=enable_shutter

                self.debug("%s: start waiting %7.3f for exposure" % (get_obsdate(),exptime))
                t_start=time.time()
                await self.ls4_controller.expose(exposure_time = exptime,\
                         exp_done_callback = exp_done_callback)
                t_wait=time.time()-t_start
                self.debug("%s: done waiting %7.3f sec for exposure, dt = %7.3f" % \
                      (get_obsdate(),self.ls4_controller.config['expose_params']['actexpt'],t_wait))
              except Exception as e:
                error_msg = "exception exposing: %s" % e

            if error_msg is None and await self.ls4_controller.is_readout_pending():
              self.debug("%s: reading out CCD to controller memory" % get_obsdate())
              #DEBUG
              wait_for = 1.0 # time (sec) to wait to allow buffer to start filling
              try:
                await self.ls4_controller.readout(wait_for=wait_for)
                self.debug("%s: waited %7.3f sec for readout" %\
                     (get_obsdate(),self.ls4_controller.config['expose_params']['read-per']))
                self.info("time to readout image: %7.3f sec" % self.timing['readout'].period)
              except Exception as e:
                error_msg = "exception reading image to controller memory: %s" % e

            # save current ls4_conf, config, and system to be used for header when data are
            #fetched
            self.fetch_ls4_conf.update(self.ls4_conf)
            self.fetch_config.update(self.ls4_controller.config)
            self.fetch_system.update(system)

        if error_msg is None and fetch and await self.ls4_controller.is_fetch_pending():
 
          # concurrent = False means the fetch can occur immediately without waiting for
          # a concurrent exposure to start or readout.
          if not concurrent:
            wait_expose = False
            wait_readout = False

          # concurrent = True  and acquire = False means another exposure may be occuring 
          # in a separate thread.
          # Set wait_expose and wait_readout so that  the fetch occurs only after the 
          # concurrent exposure has begun (wait_expose=True), or only after the concurrent
          # readout of the exposure has begun (wait_readout = True). Choose the wait option
          # depending on the exposure time. Fetching can occur during the exposure if the
          # exposure time is longer than the fetch time. Otherwise it can occur during
          # the readout, which is always longer than the fetch time.

          elif not acquire:
             if exptime > MAX_FETCH_TIME:
               wait_expose=True
               wait_readout=False
             else:
               wait_expose=False
               wait_readout=True


          self.debug("%s: fetching previously acquired image with wait_expose, wait_readout = %d,%d" %\
                 (get_obsdate(),wait_expose,wait_readout))
          try:
            await self.fetch_and_save(output_image=output_image,\
                        save=save,wait_expose=wait_expose,\
                        wait_readout=wait_readout)
          except Exception as e:
            error_msg = "Exception fetching and saving data: %s" %e


          self.debug("%s: done fetching previously acquired image with wait_expose,wait_readout = %d,%d" %\
                 (get_obsdate(),wait_expose, wait_readout))

        assert error_msg is None, error_msg
          
    async def fetch_and_save(self,output_image=None, status=None, config=None,system=None,\
                  ls4_conf=None,save=True,wait_expose=False, wait_readout=False,max_wait = MAX_FETCH_TIME):

        """
           Fetch data from last-written controller buffer and write to disk (if save = True).

           If wait_expose is True, wait up to max_wait sec for next exposure to begin before
           reading out buffer. This is to make sure the the fetch occurs as a separate thread.
           The assumption here is that the fetch time is less than the exposure time.
        """      

        error_msg = None
        self.image_data = None
        wait_timeout = False

        if status is None:
           status = self.fetch_status

        if error_msg is None:
          try:
             assert 'frame' in status,"ERROR: no frame info in status" 
          except Exception as e:
              error_msg = "%s" % e

        if error_msg is None:
          try:
             assert self.ls4_controller is not None,"ERROR: controller has not been started"
          except Exception as e:
              error_msg = "%s" % e

        if error_msg is None:
          try:
            assert not await self.ls4_controller.is_fetching(), "ERROR: controller is still fetching a different image"
          except Exception as e:
            error_msg = "%s" % e

        if error_msg is None and wait_expose and not await self.ls4_controller.is_exposing():
          self.info("%s: waiting up to %7.3f sec for exposure to begin before fetching previous exposure" %\
                   (get_obsdate(),max_wait))
          t_start = time.time()
          wait_timeout = False
          dt = 0.0
          while (not wait_timeout) and (not await self.ls4_controller.is_exposing()):
          
             if dt  > max_wait:
                wait_timeout = True
             else:
                await asyncio.sleep(0.1)
                dt += 0.1

          if wait_timeout :
            self.warn("timeout waiting %7.3f sec for exposure to begin before fetching previous buffer" % max_wait)
          else:
            self.debug("%s: done waiting for exposure to begin (waited %7.3f sec)" % \
                 (get_obsdate(),dt))


        if error_msg is None and wait_readout and not await self.ls4_controller.is_reading():
          self.debug("%s: waiting up to %7.3f sec for readout to begin before fetching previous exposure" %\
                   (get_obsdate(),max_wait))
          t_start = time.time()
          wait_timeout = False
          dt = 0.0
          while (not wait_timeout) and (not await self.ls4_controller.is_reading()):
          
             if dt  > max_wait:
                wait_timeout = True
             else:
                await asyncio.sleep(0.1)
                dt += 0.1

          if wait_timeout :
            self.warn("timeout waiting %7.3f sec for readout to begin before fetching previous buffer" % max_wait)
          else:
            self.debug("%s: done waiting for readout to begin (waited %7.3f sec)" % \
                 (get_obsdate(),dt))

        if error_msg is None:
          try:
            frame_info = status['frame']
            self.image_data,buffer_no = await self.ls4_controller.fetch(return_buffer=True, frame_info=frame_info)
            self.debug("image fetched from buffer %d" % buffer_no)
            self.info("time to fetch image: %7.3f sec" % self.timing['fetch'].period)
          except Exception as e:
            error_msg = "Exception fetching data: %s" %e

        
        if error_msg is None and save:
          self.info("saving image to %s" % output_image)
          try:
            await self.save_image(output_image=output_image)
            self.debug("time to save image: %7.3f sec" % self.timing['save'].period)
          except Exception as e:
            error_msg = "Exception saving image to %s: %s" % (output_image,e)

        
        assert error_msg is None, error_msg

    def _update_ccd_map(self):

        """ update the ccd data in the ccd_map structure with information from the
            entries controller config file (self.acf_conf). 
            Specifically, associate the taps read out by the controller with the 
            respective CCD names and their locations (A - H) in the array.

            Before updating ccd_map, it may already specify name of the CCD for each
            occupied location in the array:

               ccd_map =  ["A":{CCD_NAME":"S-003"},
                           "E":{"CCD_NAME":"S-196"}]

            The config file specifies which taps on the mother-board are being read out
            (there are 2 taps per CCD, one for each amplifier) , the readout order, the 
            orientation of the tap data in the image buffer (left or right ), 
            and the scale and offset applied to the video signal after digitization.

            For example, here are the entries for an array with 2 CCDs being read out
            through 4 taps:

              TAPLINE0="AD3L, 1, 4900"
              TAPLINE1="AD4R, 1, 1000"
              TAPLINE2="AD12L, 1, 5000"
              TAPLINE3="AD11R, 1, 700"
              TAPLINE4=
              TAPLINES=4

            These entries state there are 4 tap lines being read out in the following order:
             1:  tap index 0 : tap "AD3" with orientation "L", scale 1, and offset 4900
             2:  tap index 1 : tap "AD4" with orientation "R", scale 1, and offset 1000
             3:  tap index 2 : tap "AD12" with orientation "L", scale 1, and offset 5000
             4:  tap index 3 : tap "AD11" with orientation "R", scale 1, and offset 700

            The hard-wired mapping from tap_name to array location is given by the tap_locations
            dictionary 

             A: AD3, AD4
             B: AD2, AD1
             C: AD8, AD7
             D: AD6, AD5
             E: AD12, AD11
             F: AD10, AD9
             G: AD13, AD14
             H: AD15, AD16

            After updating, ccd_map example will be :
               ccd_map =  {"A":{"CCD_NAME":"S-003","TAP_INDICES":[0,1],"TAP_NAMES":["AD3L","AD4R"],
                                "AMP_NAMES":["LEFT","RIGHT"],"TAP_SCALES":[1,1],"TAP_OFFSETS":[4900,1000]},
                           "E":{"CCD_NAME":"S-196","TAP_INDICES":[2,3],"TAP_NAMES":["AD12L","AD11R"},
                                "AMP_NAMES":["LEFT","RIGHT"],"TAP_SCALES":[1,1],"TAP_OFFSETS":[5000,700]} }

            NOTE 1: It is possible for the config_file will be inconsistent with the ccd_map. The 
            config file may list tap names that map to unoccupied array location, or the ccd_map may
            list CCD at locations that are not list in the config file. These conditions will lead to
            raised exceptions.

            NOTE 2: If the ccd_map is uninitialized (i.e. self.ccd_map is None because no ccd_map_file was
            specified at instantiation of LS4_Camera, then this routine will fill in ccd_map 
            assuming there is an unnamed CCD at each location implicitly referenced bu the TAPLINE entries
            in the acf_config file. The ccds will be assigned names "GENERIC_CCD-A","GENERIC_CCD-B", etc depending on 
            occupied location.

        """

        # make sure acf_config includes required keywords

        assert self.acf_conf, "controller  not instantiated"
        assert "CONFIG" in self.acf_conf, "CONFIG not in acf_conf"
        assert "PIXELCOUNT" in self.acf_conf["CONFIG"], "PIXELCOUNT not in acf_conf"
        assert "LINECOUNT" in self.acf_conf["CONFIG"], "LINECOUNT not in acf_conf"
        assert "FRAMEMODE" in self.acf_conf["CONFIG"], "FRAMEMODE not in acf_conf"
        assert "TAPLINES" in self.acf_conf["CONFIG"], "TAPLINES not in acf_conf"


        #self.debug("PIXELCOUNT: %s" % self.acf_conf["CONFIG"]["PIXELCOUNT"])
        #self.debug("LINECOUNT: %s" % self.acf_conf["CONFIG"]["LINECOUNT"])

        # make sure the TAPLINES value is in range 1 to 16
        num_taps = int(self.acf_conf["CONFIG"]["TAPLINES"])
        assert num_taps >0 and num_taps<=self.max_taps,\
                "num_taps [%d] is out of range 0 to %d" % (num_taps,self.max_taps)

        # make sure the number of taps is a multiple of amps_per_ccd
        assert self.amps_per_ccd * (num_taps // self.amps_per_ccd) == num_taps,\
                "number of taps [%d] is not a multiple of amps_per_ccd [%d]" % (num_taps, self.amps_per_ccd)

        # make sure there is a "TAPLINEx" entry in acf_conf for each tap_index from 0 to num_taps-1.
        # Also make sure there are three values specified for each tap_index (tap_name,scale,offset).
        # save these data in tap_info.

        tap_info=[]
        for tap_index in range(0,num_taps):
          key="TAPLINE%d" % tap_index
          assert key in self.acf_conf["CONFIG"], "key %s not in acf_conf" % key
          data = self.acf_conf["CONFIG"][key].replace('"','')
          data = data.split(",")
          assert len(data) == 3, "unexpected data for key %s: %s" % (key,data)
          #put the data into a dictionary format
          info= {"TAP_NAME":data[0].upper(),\
                 "TAP_INDEX":tap_index,\
                  "TAP_SCALE":int(data[1]),\
                  "TAP_OFFSET":int(data[2])}
          tap_info.append(info)

        # record relevant config info in self.image_info
        self.image_info['pixels'] = int(self.acf_conf["CONFIG"]["PIXELCOUNT"])
        self.image_info['lines'] = int(self.acf_conf["CONFIG"]["LINECOUNT"])
        self.image_info['frame_mode'] = int(self.acf_conf["CONFIG"]["FRAMEMODE"])
        self.image_info['num_taps'] = num_taps

        # create tap_data list to store information for each tap index
        # Each entry will have the following format:
        # {"LOCATION":location,"AMP_NAME":amp_name,"TAP_NAME":tap_name,"TAP_INDEX":tap_index,"TAP_SCALE":tap_scale,"TAP_OFFSET":tap_offset}

        tap_data = []
        for tap_index in range(0,num_taps):

          # get info for this tap index
          info=tap_info[tap_index]

          # get the location info  for this tap .
          # location info is, for example: {"LOCATION":"B","AMP_NAME":"LEFT"}
          location_info =  self._get_tap_location_info(info["TAP_NAME"])

          # add the location info to the tap_data for this tap_index
          info.update(location_info)

          tap_data.append(info)


        # if ccd_map is not initialized, fill it with dummy CCD names, one at
        # each location referenced by tap_data
        if self.ccd_map is None:
          self.ccd_map={}
          for tap_info in tap_data:
             location=tap_info["LOCATION"]
             if location not in self.ccd_map:
                ccd_name = "GENERIC_CCD-"+location
                self.ccd_map[location]={"CCD_LOC":ccd_name}

        # Make sure each ccd location in ccd_map has 1 or 2 entries in tap_data
        # (one for each amp that may be read out).
        
        for location in self.ccd_map:
           num_matched=0
           for entry in tap_data:
               if entry["LOCATION"] == location:
                  num_matched += 1
           assert num_matched > 0, \
              "occupied ccd location %s does not appear in tap data of acf file" % location
           assert num_matched < 3, \
              "occupied ccd location %s appears more than twice in tap data of acf file" % location

        # Make sure each tap index in tap_data has a location with a  matching an entry in ccd_map.

        for tap_info in tap_data:
           location=tap_info["LOCATION"]
           assert location in self.ccd_map, \
                "ccd location %s is read out (tap_index %d) but does not appear in tap_map" % \
                 (location,tap_index)

        # add the info in each tap_data entry to the respective entries in ccd_map.
        # key_map gives the correspondences between the entry keys.
        key_map={"AMP_NAME":"AMP_NAMES","TAP_NAME":"TAP_NAMES",\
                "TAP_INDEX":"TAP_INDICES","TAP_SCALE":"TAP_SCALES",\
                "TAP_OFFSET":"TAP_OFFSETS"}

        for t_info in tap_data:
            location = t_info["LOCATION"]
            ccd_info = self.ccd_map[location]
            #print("ccd_info: %s" % ccd_info)
            for tap_key in key_map:
                ccd_key =key_map[tap_key]
                if tap_key in t_info:
                   data = t_info[tap_key]
                   if ccd_key not in ccd_info:
                      ccd_info[ccd_key]=[]
                   ccd_info[ccd_key].append(data)
 
        self.image_info['num_ccds'] = len(self.ccd_map)


    def _get_amp_selection (self,amp_index):

        """ Return LEFT, RIGHT, ... depending on value of amp_index """

        if  amp_index not in range(0,self.amps_per_ccd):
            self.warn("amp_index [%d] out of range [0 to %d]" % (amp_index, self.amps_per_ccd))
            return None

        if amp_index == 0:
           return "LEFT"
        elif amp_index == 1:
           return "RIGHT"
        else:
           return None

    def _get_tap_location_info(self,tap_name=""):

        """ given tap name, return tap location info """

        name = tap_name.upper()
        name = name.replace("L","").replace("R","")
        assert name in self.tap_locations, "invalid tap name %s" % tap_name
        return self.tap_locations[name]

    def _get_ccd_location(self,ccd_name=None,tap_name=None):

        """ given ccd_name or tap_name, return ccd location"""

        assert ccd_name is not None or tap_name is not None,\
            "neither ccd_name or tap_name is specified"

        ccd_location = None

        if ccd_name is not None:
          ccd_name = ccd_name.upper()
          for location, ccd_info in self.ccd_map:
             if ccd_info["CCD_LOC"] == ccd_name:
               ccd_location = location

        elif tap_name is not None:
           try:
             location_info=self._get_tap_location_info(tap_name)
           except Exception as e:
             self.error("failed to get location for tap %s: %s" % (tap_name,e))

        assert ccd_location is not None,\
           "failed to get ccd_location for ccd_name %s and tap_name %s" %\
                (ccd_name,tap_name)

        return ccd_location


    def _get_tap_data(self,ccd_name=None,ccd_location=None,amp_name=None,data_key=None):

        """ given ccd name or location, return data specified by data_key.
            if amp_name is "BOTH" or None, return the data for both amps.
            If amp is "LEFT" or "RIGHT", return only the data for the specified amp.

            The data are returned as a list
        """

        assert data_key in ["AMP_NAMES","TAP_NAMES","TAP_INDICES","TAP_SCALES""TAP_OFFSETS"],\
                "invalid data_key: %s" % data_key

        assert ccd_name is not None or ccd_location is not None,\
                "both ccd_name and ccd_location are unspecified"

        assert (amp_name is None) or (amp_name in ["LEFT","RIGHT","BOTH"]),\
               "amp_name %s must be LEFT,RIGHT,BOTH, or None" % amp_name

        
        info = None
        # retrieve the info from ccd_map for the specified ccd location
        if ccd_location is not None:
           location = ccd_location.upper()
           assert location in self.ccd_map, "ccd location %s is not in ccd_map" % location
           info = self.ccd_map[location]

        # or else retrieve the info from ccd_map for the specified ccd name
        else:
           name = ccd_name.upper()
           for entry in self.ccd_map:
               if "CCD_LOC" in entry and name  == entry["CCD_LOC"]:
                   info = entry
           
        assert info is not None, "no ccd info found for ccd name %s or location %s" %\
                    (ccd_name,ccd_location)

        key = data_key.upper()
        assert key in info, "no data_key named %s found for ccd name %s or location %s" %\
                    (data_key,ccd_name,ccd_location)

        data = info[key]
        if amp_name in ['LEFT','RIGHT']:
          assert len(data) >= 1, "expected one entries for %s, but found %d" % (key,len(data))
        else:
          assert len(data) == 2, "expected two entries for %s, but found %d" % (key,len(data))
          

        if amp_name is None or  amp_name.upper() == "BOTH":
           return data
        elif amp_name.upper() == "LEFT":
           return [data[0]]
        else:
           return [data[1]]


    def _get_tap_indices(self,ccd_name=None,ccd_location=None, amp_name=None):

        """ given ccd name or location, return tap indices"""

        return self._get_tap_data(ccd_name=ccd_name,ccd_location=ccd_location,\
                amp_name=amp_name,data_key="TAP_INDICES")

    def update_header(self,header=None,conf=None,reject_keys={}):

        """ update header with key,value pairs in given configuration dictionary """

        for key in conf:
          if key not in reject_keys:
            try:  
              value=conf[key]
              if isinstance(value,(dict,list,tuple)):
                 if len(value) == 0:
                    value = None
              elif isinstance(value,str):
                 if len(value) == 0:
                    value = None
                 elif len(key+value)>70:
                    value = value[:70]
              #self.debug("key: %s  value: %s" % (key,value))
              header.update({key:value})
            except Exception as e:
              self.error("Exception updating update header with configuration key,value %s %s: %s" %\
                        (key,dict[key],e))


    def _get_header_info(self,header={},conf=None,ccd_location=None,amp_index=None):


        """
            build a fits header for specifed CCD and ccd amplifire using information in
            self.ccd_map, self.image_info, status, and system
        """

        #  example ccd_map:
        #      ccd_map =  {"A":{"CCD_NAME":"S-003","TAP_INDICES":[0,1],"TAP_NAMES":["AD3L","AD4R"],
        #                       "AMP_NAMES":["LEFT","RIGHT"],"TAP_SCALES":[1,1],"TAP_OFFSETS":[4900,1000]},
        #                  "E":{"CCD_NAME":"S-196","TAP_INDICES":[2,3],"TAP_NAMES":["AD12L","AD11R"},
        #                       "AMP_NAMES":["LEFT","RIGHT"],"TAP_SCALES":[1,1],"TAP_OFFSETS":[5000,700]} }

        if conf is not None:
          reject_keys=[]
          h={}
          h.update(header)
          for key in conf:
             #if "_list" in key or 'log_format' in key or 'frame' in key:
             if "_list" in key or 'log_format' in key:
                reject_keys.append(key)
             elif isinstance(conf[key],(dict)):
                h.update(conf[key])
             elif isinstance(conf[key],(list,tuple)):
                pass
             else:
                h[key]=conf[key]

          self.update_header(header=header,conf=h,reject_keys=reject_keys)

        elif ccd_location is not None:
          try:
            assert amp_index is not None, "unspecified amp index"
            assert ccd_location in self.ccd_map, "ccd location %s not found in ccd map" % ccd_location
            assert amp_index in range(0,self.amps_per_ccd),\
                    "amp_index [%d] out of range [0 to %d]" % (amp_index,self.amps_per_ccd)
          except Exception as e:
            self.error(e)
            return 

          key_map={"AMP_NAME":"AMP_NAMES","TAP_NAME":"TAP_NAMES",\
                  "TAP_INDEX":"TAP_INDICES","TAP_SCALE":"TAP_SCALES",\
                  "TAP_OFFSET":"TAP_OFFSETS"}

          ccd_info = self.ccd_map[ccd_location]
          header.update({"CCD_LOC":ccd_info["CCD_LOC"]})
          header.update({"CCD_NAME":ccd_info["CCD_NAME"]})

          for key in key_map:
              k = key_map[key]
              value = ccd_info[k][amp_index]
              header.update({key:value})
             
        return header


    def _get_ccd_data(self,ccd_location=None,ccd_name=None,amp_selection=None):

        """ return a list of 2-D numpy arrays with image data for a specifed ccd name or location.
            The data are extracted from the data buffer fetched from the controller.

            ccd_name is the serial number of the ccd (e.g."S-196")
            ccd_location is the slot in the LS4 mother board ("A","B",...,"H")
            amp_selection can be "LEFT", "RIGHT", "BOTH".

            For a given ccd, the location of the corresponding image data within the 
            frame buffer depends on the corresponding tap_indices recorded
            in ccd_map and the data storage mode ("top", "bottom" or "split") 

            Each amp of each CCD yields a sub-image with row length = "pixels" and
            number of rows = "lines".

            If only one tap is selected, then the returned data is a numpy array of
            dimensions [lines:pixels].
            If 2/2 taps are selected, the dimension is [lines:2*pixels].

            Large number of taps per ccd are not supported.
        """

        ccd_data = None

        num_taps = self.image_info['num_taps']
        num_ccds = self.image_info['num_ccds']

        try:
          assert  (ccd_location is not None) or (ccd_name is not None),\
                  "unspecified values for ccd_location and ccd_name"
          assert  amp_selection is not None, "unspecified amp selection"

          assert  amp_selection.upper() in ["LEFT","RIGHT","BOTH"],\
                  "tap number must be in LEFT, RIGHT, or BOTH"

          assert  num_ccds in range(1,9),\
                    "number of taps must be 1 to 8, not %d" % num_ccds

          assert  num_taps == num_ccds * self.amps_per_ccd,\
                    "number of taps must be 1 or 2, not %d" % num_taps
        except Exception as e:
          raise ValueError(e)

        # retrieve the tap indices for this ccd.
        tap_indices =  None
        try:
           tap_indices = self._get_tap_indices(ccd_location=ccd_location,\
                   ccd_name = ccd_name, amp_name = amp_selection)
        except Exception as e:
           self.error("exception getting  tap indices for ccd_name %s or ccd_location %s: %s" %\
                   (ccd_name, ccd_location,e))
           raise RuntimeError(e)
         
        if tap_indices is None:
           raise RuntimeError("tap indices for ccd at location [%s] with name [%s] are unknown" %\
                       (ccd_location, ccd_name))

      

        framemode_int = int(self.acf_conf["CONFIG"]["FRAMEMODE"])
        if framemode_int == 0:
            framemode = "top"
        elif framemode_int == 1:
            framemode = "bottom"
        else:
            framemode = "split"


        if framemode == "top":
            # Each row of the image corresponds is one long row composed of the corresponding rows of 
            # the sub-images, all stacked together (the total row length is num_ccds*num_taps*pixels).
            # The number of rows is the same as the number of rows of each sub image.

            ccd_data = []
            for tap_index in tap_indices:
              x0 = tap_index * self.image_info['pixels'] 
              x1 = x0 +  self.image_info['pixels']
              y0 = 0
              y1 = y0 + self.image_info['lines']
              ccd_data.append(self.image_data[y0:y1, x0:x1])


        elif framemode == "split":
            # The image is constructed of n blocks, where n is the number of amps per ccd.
            # Each block, i, is constructed like a "top-mode" image, but only from the 
            # i-th amplifier of each CCD (with only 2 amps per ccd, there two blocks -- one for
            # the left amp, the other for the right amp).
            # These blocks are stacked on top of each other.
            # Each row has length num_ccds * pixels and the number of rows is num_ccds * num_taps


            ccd_data = []
            j = 0
            for  tap_index in tap_indices:
              x0 = (tap_index // num_taps) * self.image_info['pixels'] 
              x1 = x0 +  self.image_info['pixels']
              y0 + self.image_info['lines'] * j
              y1 = y0 + self.image_info['lines'] 
              ccd_data.append(self.image_data[y0:y1, x0:x1])
              j += 1


        else:
            raise ValueError(f"Framemode {framemode} is not supported at this time.")

        return ccd_data
