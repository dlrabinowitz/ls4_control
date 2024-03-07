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
from archon import log
import logging
from archon.ls4.ls4_sync import LS4_Sync
from archon.controller.ls4_controller import LS4Controller
from archon.controller.maskbits import ArchonPower
from astropy.io import fits
import json
import time
import argparse
#from . import MAX_COMMAND_ID,FOLLOWER_TIMEOUT_MSEC
from . import VOLTAGE_TOLERANCE

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

    amps_per_ccd = 2
    max_ccds = 8
    max_taps = amps_per_ccd * max_ccds

    required_conf_params = ['data_path','acf_file','test','log_level','ip','name']
    default_params = {'data_path':'/tmp','test':False,'log_level':'INFO','ip':'10.0.0.2','name':'ctrlx','local_addr':('127.0.0.1',4242)}

    def __init__(self,ls4_conf=None,param_args=None,command_args=None):
       
        """ ls4_conf is a dictionary with configuration variables for the instance of LS4_Camera.

            param_args is a list with one entry -- a dictionary to hold parameter arguments 
            for sync_set_param. It is set up as a list so that any changes to the dictionary
            contents are inherited by all threads sharing param_args. 

            command_args is  also a list with one entry -- a dictionary to hold command arguments 
            for sync_send_commnd. It is set up as a list so that any changes to the dictionary
            contents are inherited by all threads sharing command_args
        """

        self.leader = False
        self.prefix = ""

        assert ls4_conf is not None,"unspecified configuration"
        assert param_args is not None,"unspecified param_args"
        assert command_args is not None,"unspecified command_args"
        assert len(param_args)==1, "param_args is not a list of length 1"
        assert len(command_args)==1, "command_args is not a list of length 1"

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

        #self.log = log

        if 'log_format' in ls4_conf and ls4_conf['log_format'] is not None:
          self.debug("setting log format to %s" % ls4_conf['log_format'])
          try:
             logging.basicConfig(format=ls4_conf['log_format'])
          except Exception as e:
             self.warn("unable to set log format to %s" % ls4_conf['log_format'])


        log_level=ls4_conf['log_level']
        log.setLevel(logging.NOTSET)
        if log_level in ["DEBUG","debug","Debug"]:
           log.setLevel(logging.DEBUG)
        elif log_level in ["INFO","info","Info"]:
           log.setLevel(logging.INFO)
        elif log_level in ["WARN","warn","Warn"]:
           log.setLevel(logging.WARNING)
        elif log_level in ["ERROR","error","Error"]:
           log.setLevel(logging.ERROR)
        elif log_level in ["CRITICAL","critical","Critical"]:
           log.setLevel(logging.CRITICAL)


        self.debug('ls4_conf:')
        #for key in ls4_conf:
        #    self.info("%20s : %s" % (key,ls4_conf[key]))

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

        #if self.ccd_map is not None:
        #  self.info("initial ccd_map is %s" % self.ccd_map)
    
        self.ls4_conf = ls4_conf
 
        # self.param_args[0] is a shared global
        self.param_args = param_args

        # self.command_args[0] is a shared global
        self.command_args = command_args


    def info(self,str):
      if self.leader or self.name == "ctrl1":
        str1 = "%s: "%self.name + str
        #self.log.info(str1)
        log.info(str1)
        sys.stdout.flush()
    def error(self,str):
        str1 = "%s: "%self.name + str
        log.error(str1)
        sys.stdout.flush()
    def warn(self,str):
        str1 = "%s: "%self.name + str
        log.warn(str1)
        sys.stdout.flush()
    def debug(self,str):
      if self.leader or self.name == "ctrl1":
        str1 = "%s: "%self.name + str
        log.debug(str1)
        sys.stdout.flush()
    def critical(self,str):
        str1 = "%s: "%self.name + str
        log.critical(str1)
        sys.stdout.flush()

    def set_lead(self, lead_flag: bool = False):
        self.leader = lead_flag
        self.prefix = "leader %s:" % self.name
        if self.ls4_controller is not None:
           self.ls4_controller.set_lead(lead_flag)

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
        self.info(str)

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


    async def power_down(self):
        result = None
        try:
          result = await self.ls4_controller.power(mode=False)
        except Exception as e:
          self.error("exception powering down controller: %s" %e)
          return None

        return result

    async def power_up(self):
        result = None
        try:
          result = await self.ls4_controller.power(mode=True)
        except Exception as e:
          self.error("exception powering up controller: %s" %e)
          return None

        assert await self.check_voltages(), "voltages out of range" 
        return result

    async def start_autoflush(self):
        try:
          await self.ls4_controller.set_autoflush(mode=True)
        except Exception as e:
          self.error("exception starting autoflushr: %s" %e)
          
    async def stop_autoflush(self):
        try:
          await self.ls4_controller.set_autoflush(mode=False)
        except Exception as e:
          self.error("exception starting autoflushr: %s" %e)
          
    async def init_controller(self,hold_timing=False):
        """ if hold_timing is True, set the controller state to hold off executing the timing
            script when the config file is loaded by start_controller().
        """
 
        error_msg = None
        cmd = None

        try:
          assert self.ls4_controller == None,"controller already started"
        except Exception as e:
          error_msg = "%s" % e

        if error_msg is None:
          try:
            self.ls4_controller = LS4Controller(name=self.name,\
                 host=self.ip_address,local_addr=self.local_addr,\
                 param_args=self.param_args,command_args=self.command_args)
            self.info("awaiting ac.start")
            await self.ls4_controller.start(reset=False)
          except Exception as e:
            error_msg = "exception starting archon controller: %s" % e

        if error_msg is None and hold_timing is True:
          try:
            self.debug("hold timing until after config file is loaded")
            await self.hold_timing()
          except Exception as e:
            error_msg = "exception holding timing for archon controller: %s" % e

        #print("error_msg is %s" % error_msg)
        if error_msg:
            self.error(error_msg)
            raise RuntimeError(error_msg)
        else:
            self.info("controller initialized")

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
        """ if release_timing is False, the controller will not start its timing scripts until
            self.ls4_controller.release_timing() is later executed. This synchronizes
            the timing scripts for controller connected by sync cables
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
                             notifier=self.notifier,applyall=False,poweron=False)
            else:
              await self.ls4_controller.write_config(release_timing=release_timing,\
                             input=self.acf_conf_file,\
                             notifier=self.notifier,applyall=True,poweron=True)
          except Exception as e:
            error_msg = "exception writing acf_conf_file to controller: %s" % e


        if power_on and error_msg is None:
           try:
              assert await self.check_voltages(), "voltages out of range"
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

    async def save_image(self,output_image=None, status=None, system=None):

        image_index = 0
        header_info0 = {}
        header_info0 = self._get_header_info(header_info0,conf = self.ls4_conf)
        header_info0 = self._get_header_info(header_info0,conf = self.ls4_controller.config['expose params'])
        header_info0 = self._get_header_info(header_info0,conf = self.ls4_controller.config['archon'])
        header_info0 = self._get_header_info(header_info0,conf = status)
        header_info0 = self._get_header_info(header_info0,conf = system)


        for ccd_location in self.ccd_map:
          for amp_index in range(0,self.amps_per_ccd):
            amp_selection = self._get_amp_selection(amp_index)
            if amp_selection is not None:
                ccd_data_list = self._get_ccd_data(ccd_location=ccd_location,amp_selection=amp_selection)
                ccd_data = ccd_data_list[0]
                #self.info("ccd_data shape: %s" % str(ccd_data.shape))
                image_name =  output_image.replace(".fits","")
                image_name = image_name + "_%d"%image_index + ".fits"

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
                  header[key] = header_info[k]

                hdul = fits.HDUList([hdu])
                hdul.writeto(image_name,overwrite=True)
                hdul.close()
                try:
                  del hdu
                except:
                  pass
                image_index += 1
         
    async def check_voltages(self,status=None,voltage_tolerance=VOLTAGE_TOLERANCE):
        """ check that voltages are within desired tolerance """

        in_tolerance = True

        if status is None:
          status = await self.get_status()

        conf_keys=[\
          'mod4\\lvhc_v1',\
          'mod4\\lvhc_v2',\
          'mod4\\lvhc_v3',\
          'mod4\\lvhc_v4',\
          'mod4\\lvhc_v5',\
          'mod4\\lvhc_v6',\
          'mod9\\xvn_v1',\
          'mod9\\xvn_v2',\
          'mod9\\xvn_v3',\
          'mod9\\xvn_v4',\
          'mod9\\xvp_v1',\
          'mod9\\xvp_v2',\
          'mod9\\xvp_v3',\
          'mod9\\xvp_v4',\
          ]

        supply_voltage_keys=[\
          'p5v_v',\
          'p6v_v',\
          'n6v_v',\
          'p17v_v',\
          'n17v_v',\
          'p35v_v',\
          'n35v_v',\
          'p100v_v',\
          'n100v_v',\
          ]

        status_keys=[\
            'mod4/lvhc_v1',\
            'mod4/lvhc_v2',\
            'mod4/lvhc_v3',\
            'mod4/lvhc_v4',\
            'mod4/lvhc_v5',\
            'mod4/lvhc_v6',\
            'mod9/xvn_v1',\
            'mod9/xvn_v2',\
            'mod9/xvn_v3',\
            'mod9/xvn_v4',\
            'mod9/xvp_v1',\
            'mod9/xvp_v2',\
            'mod9/xvp_v3',\
            'mod9/xvp_v4',\
            'p5v_v',\
            'p6v_v',\
            'n6v_v',\
            'p17v_v',\
            'n17v_v',\
            'p35v_v',\
            'n35v_v',\
            'p100v_v',\
            'n100v_v',\
            ]

        conf_enable_keys=[\
            'mod4\\lvhc_enable1',\
            'mod4\\lvhc_enable2',\
            'mod4\\lvhc_enable3',\
            'mod4\\lvhc_enable4',\
            'mod4\\lvhc_enable5',\
            'mod4\\lvhc_enable6',\
            'mod9\\xvn_enable1',\
            'mod9\\xvn_enable2',\
            'mod9\\xvn_enable3',\
            'mod9\\xvn_enable4',\
            'mod9\\xvp_enable1',\
            'mod9\\xvp_enable2',\
            'mod9\\xvp_enable3',\
            'mod9\\xvp_enable4',\
            ]


        if self.ls4_controller is not None:
          conf = self.ls4_controller.acf_config["CONFIG"]
          index = 0
          for c_key in conf_keys:
            s_key = status_keys[index]
            c_enable_key = conf_enable_keys[index]
            assert c_key in conf, "config key %s not found in conf" % c_key
            assert c_enable_key in conf, "config key %s not found in conf" % c_enable_key
            assert s_key in status, "status key %s not found in status" % s_key
            if conf[c_enable_key] in [1,"1"]:
              v_in = float(conf[c_key])
              v_out = status[s_key]
              if  np.fabs(v_in-v_out) > max(voltage_tolerance,0.01*np.fabs(v_in)):
                 self.warn("voltage %s is out of tolerance: set: %7.3f actual: %7.3f" % (c_key,v_in,v_out))
                 in_tolerance = False
              else:
                 self.debug("voltage %s is in range: set: %7.3f actual: %7.3f" % (c_key,v_in,v_out))
            index += 1

          assert "supply voltages" in self.ls4_controller.config, "no supply voltages in config"
          conf = self.ls4_controller.config["supply voltages"]
          self.debug("conf = %s" % str(conf))
          for supply_key in supply_voltage_keys:
            assert supply_key in conf, "supply_voltage key %s not found in conf" % supply_key
            assert supply_key in status, "supply_voltage key %s not found in status" % supply_key
            v_in = float(conf[supply_key])
            v_out = status[supply_key]
            if np.fabs(v_in)>40.0:
               v_tol = 3.0
            else:
               v_tol = voltage_tolerance
            v_tol =  max(v_tol,0.01*np.fabs(v_in))
            if np.fabs(v_in-v_out) > v_tol:
               self.warn("supply voltage %s is out of tolerance: set: %7.3f actual: %7.3f tol: %7.3f" %\
                       (supply_key,v_in,v_out,v_tol))
               in_tolerance = False
            else:
               self.debug("supply voltage %s is in range: set: %7.3f actual: %7.3f" % (c_key,v_in,v_out))

        return in_tolerance

    async def acquire(self,output_image=None,exptime=0.0, acquire=True, fetch=True, save=True):
        error_msg = None
        cmd = None
        self.image_data = None

        self.debug("acquire with output: %s exptime: %7.3f acquire: %s  fetch:  %s  save: %s" %\
               (output_image,exptime,acquire,fetch,save))
        try:
           assert self.ls4_controller is not None,"controller has not been started"
        except Exception as e:
           error_msg = e

        if error_msg is None:
          status = await self.get_status()
          system = await self.get_system()

        if error_msg is None:

          if self.ls4_test or acquire==False:
             self.debug("ls4_test mode: skipping aquisition of image")
          else:
            try:
              assert await self.check_voltages(status),"voltages out of range first check"
            except Exception as e:
              error_msg = e

            if error_msg is None:
              self.debug("start exposing %7.3f sec. Trigger readout only:" % exptime)
              try:
                self.info("waiting for exposure")
                await self.ls4_controller.expose(exptime, readout=False)
                self.info("waited %7.3f sec for exposure" % self.ls4_controller.config['expose params']['exptime'])
              except Exception as e:
                error_msg = "exception exposing: %s" % e

        if error_msg is None:
          if self.ls4_test or acquire==False:
             self.debug("ls4_test mode: skipping readout of image")
          else:
            self.debug("reading out CCD to controller memory")
            try:
              if self.ls4_controller.ls4_sync_io.leader:
                 wait_for = 1.0
              else:
                 #DEBUG
                 #wait_for = 0.0
                 wait_for = 1.0
              await self.ls4_controller.readout(notifier=self.notifier,wait_for=1.0)
            except Exception as e:
              error_msg = "exception reading out to controller memory: %s" % e

        if error_msg is None and fetch:
          self.info("fetching data:")
          try:
            await self.fetch_and_save(output_image=output_image,status=status,system=system,save=save)
          except Exception as e:
            error_msg = "Exception fetching and saving data: %s" %e

        assert error_msg is None, error_msg
          
    async def fetch_and_save(self,output_image=None, status=None, system=None,save=True):
        error_msg = None
        self.image_data = None

        try:
           assert self.ls4_controller is not None,"ERROR: controller has not been started"
        except Exception as e:
            error_msg = "%s" % e

        if error_msg is None:
          #self.info("fetching data:")
          try:
            self.image_data,buffer_no = await self.ls4_controller.fetch(return_buffer=True)
            self.debug("image fetched from buffer %d" % buffer_no)
          except Exception as e:
            error_msg = "Exception fetching data: %s" %e

        
        if error_msg is None and save:
          self.info("saving image to %s" % output_image)
          try:
            await self.save_image(output_image=output_image,status=status,system=system)
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


        self.debug("PIXELCOUNT: %s" % self.acf_conf["CONFIG"]["PIXELCOUNT"])
        self.debug("LINECOUNT: %s" % self.acf_conf["CONFIG"]["LINECOUNT"])

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
                self.ccd_map[location]={"CCD_NAME":ccd_name}

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
            print("ccd_info: %s" % ccd_info)
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
             if ccd_info["CCD_NAME"] == ccd_name:
               ccd_location = location

        elif tap_name is not None:
           try:
             location_info=self._get_tap_location_info(tap_name)
           except Exception as e:
               self.info("failed to get location for tap %s: %s" % (tap_name,e))

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
               if "CCD_NAME" in entry and name  == entry["CCD_NAME"]:
                   info = entry
           
        assert info is not None, "no ccd info found for ccd name %s or location %s" %\
                    (ccd_name,ccd_location)

        key = data_key.upper()
        assert key in info, "no data_key named %s found for ccd name %s or location %s" %\
                    (data_key,ccd_name,ccd_location)

        data = info[key]
        assert len(data) == 2, "expected two entries for %s, but found %d" % (key,len(data))
          
        #self.info("for ccd location: %s ccd_name: %s amp_name: %s data are %s" %\
        #       (ccd_location,ccd_name,amp_name,str(data)))

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
              self.debug("key: %s  value: %s" % (key,value))
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
          for key in conf:
             if "_list" in key or 'log_format' in key:
                reject_keys.append(key)
          self.update_header(header=header,conf=conf,reject_keys=reject_keys)

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
          ccd_name = ccd_info["CCD_NAME"]
          header.update({"CCD_NAME":ccd_name})

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

      
        #self.info("num_taps: %d" % num_taps)
        #self.info("num_ccds: %d" % num_ccds)
        #self.info("pixels: %d" % self.image_info['pixels'])
        #self.info("lines: %d" % self.image_info['lines'])
        #self.info("raw image shape: %s" % str(self.image_data.shape))

        # retrieve the tap indices for this ccd.
        tap_indices =  None
        try:
           tap_indices = self._get_tap_indices(ccd_location=ccd_location,\
                   ccd_name = ccd_name, amp_name = amp_selection)
        except Exception as e:
           self.info("exception getting  tap indices for ccd_name %s or ccd_location %s: %s" %\
                   (ccd_name, ccd_location,e))
           raise RuntimeError(e)
         
        if tap_indices is None:
           raise RuntimeError("tap indices for ccd at location [%s] with name [%s] are unknown" %\
                       (ccd_location, ccd_name))

      
        #self.info("tap indices are %s" % str(tap_indices))

        framemode_int = int(self.acf_conf["CONFIG"]["FRAMEMODE"])
        if framemode_int == 0:
            framemode = "top"
        elif framemode_int == 1:
            framemode = "bottom"
        else:
            framemode = "split"

        #self.info("frame mode is %s" % framemode)

        if framemode == "top":
            # Each row of the image corresponds is one long row composed of the corresponding rows of 
            # the sub-images, all stacked together (the total row length is num_ccds*num_taps*pixels).
            # The number of rows is the same as the number of rows of each sub image.

            ccd_data = []
            for tap_index in tap_indices:
              #self.info("extracting data for ccd location: %s ccd_name: %s amp_selection: %s tap_index %d" %\
              # (ccd_location,ccd_name, amp_selection,tap_index))
              x0 = tap_index * self.image_info['pixels'] 
              x1 = x0 +  self.image_info['pixels']
              y0 = 0
              y1 = y0 + self.image_info['lines']
              #self.info("appending raw data im range y [%d to %d] and x[%d to %d]"%\
              #       (y0,y1,x0,x1))
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
