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
from archon.ls4.ls4_header import LS4_Header 
from archon.ls4.ls4_ccd_map import LS4_CCD_Map
from astropy.io import fits
from archon.tools import get_obsdate
import json
import time
import argparse

from . import VOLTAGE_TOLERANCE, MAX_FETCH_TIME, AMPS_PER_CCD, MAX_CCDS, VSUB_BIAS_NAME

class LS4_Camera():

    required_conf_params = ['data_path','acf_file','test','log_level','ip','name','map_file']
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
        self.ls4_ccd_map = None
        self.ls4_header = None

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


        self.debug("instantiating ls4_ccd_map")
        try: 
          self.ls4_ccd_map=LS4_CCD_Map(ls4_conf=ls4_conf,ls4_logger=self.ls4_logger)
        except Exception as e:
          raise RuntimeError("unable to instantiate ls4_ccd_map: %s" % e)

        self.ls4_conf = ls4_conf

        self.ls4_header = LS4_Header(ls4_logger = self.ls4_logger, ls4_conf = self.ls4_conf, ls4_ccd_map = self.ls4_ccd_map)
 
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
            self.ls4_controller = LS4Controller(name=self.name,\
                 host=self.ip_address,local_addr=self.local_addr,\
                 param_args=self.param_args,command_args=self.command_args,
                 ls4_events = self.ls4_sync.ls4_events,
                 ls4_logger=self.ls4_logger,
                 fake=self.fake_controller,
                 timing=self.timing,
                 reboot=reboot,
                 idle_function =  self.ls4_conf['idle_function'],
                 acf_file = self.acf_conf_file,
                 notifier=self.notifier)
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
          ## ccd_map must be updated with dictionary of info updated by ls4_controller instance
          try:
            self.ls4_ccd_map.update(acf_conf = self.ls4_controller.acf_config)
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

        # initialize header info common to all CCD sub-images
        image_index = 0
        self.ls4_header.initialize()
        self.ls4_header.set_header_info(conf = ls4_conf)
        self.ls4_header.set_header_info(conf = config['expose_params'])
        self.ls4_header.set_header_info(conf = config['archon'])
        self.ls4_header.set_header_info(conf = status)
        self.ls4_header.set_header_info(conf = system)

        amps_per_ccd = self.ls4_ccd_map.image_info['amps_per_ccd']

        # for each amplifier of each ccd,  set info0 specific to the
        # respective image data

        for ccd_location in self.ls4_ccd_map.ccd_map:
          for amp_index in range(0,amps_per_ccd):
            amp_selection = self.ls4_ccd_map.get_amp_selection(amp_index)
            if amp_selection is not None:
                ccd_data_list = self._get_ccd_data(ccd_location=ccd_location,amp_selection=amp_selection)
                ccd_data = ccd_data_list[0]
                image_name =  output_image.replace(".fits","")
                image_name = image_name + "_%02d"%image_index + ".fits"

                header_info = self.ls4_header.set_header_info(ccd_location=ccd_location, amp_index = amp_index)

                hdu = fits.PrimaryHDU(ccd_data)
                fits_header = hdu.header
                for k in header_info:
                  key = k
                  if len(key.rstrip())>8:
                     key = "HIERARCH "+ key
                 
                  if isinstance(header_info[k],(float,)) and k in ["actexpt","read_per"]:
                     header_info[k] = round(header_info[k],3)
                  fits_header[key] = header_info[k]

                hdul = fits.HDUList([hdu])
                hdul.writeto(image_name,overwrite=True)
                hdul.close()
                try:
                  del hdu
                except:
                  pass
                image_index += 1

        self.timing['save'].end()
    
    async def acquire(self,output_image=None,exptime=0.0, acquire=True, fetch=True, \
                        concurrent=False, save=True, enable_shutter=True):

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
                await self.ls4_controller.expose(exptime)
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


        try:

          assert self.ls4_ccd_map is not None,\
                  "ls4_ccd_map is not instantiated"
          assert self.ls4_ccd_map.image_info is not None,\
                  "ls4_ccd_map.image_info is not instantiated"
          assert 'num_ccds' in self.ls4_ccd_map.image_info,\
                  "num_ccds not a member of ls4_ccd_map.image_info"
          assert 'num_taps' in self.ls4_ccd_map.image_info,\
                  "num_taps not a member of ls4_ccd_map.image_info"
          assert 'num_lines' in self.ls4_ccd_map.image_info,\
                  "lines not a member of ls4_ccd_map.image_info"
          assert 'num_pixels' in self.ls4_ccd_map.image_info,\
                  "pixels not a member of ls4_ccd_map.image_info"
          assert 'amps_per_ccd' in self.ls4_ccd_map.image_info,\
                  "amps_per_ccd  not a member of ls4_ccd_map.image_info"
        except Exception as e:
          raise ValueError(e)

        num_taps = self.ls4_ccd_map.image_info['num_taps']
        num_ccds = self.ls4_ccd_map.image_info['num_ccds']
        num_pixels = self.ls4_ccd_map.image_info['num_pixels']
        num_lines = self.ls4_ccd_map.image_info['num_lines']
        amps_per_ccd = self.ls4_ccd_map.image_info['amps_per_ccd']

        try:
          assert  (ccd_location is not None) or (ccd_name is not None),\
                  "unspecified values for ccd_location and ccd_name"
          assert  amp_selection is not None, "unspecified amp selection"

          assert  amp_selection.upper() in ["LEFT","RIGHT","BOTH"],\
                  "tap number must be in LEFT, RIGHT, or BOTH"

          assert  num_ccds in range(1,9),\
                    "number of taps must be 1 to 8, not %d" % num_ccds

          assert  num_taps == num_ccds * amps_per_ccd,\
                    "number of taps must be 1 or 2, not %d" % num_taps
        except Exception as e:
          raise ValueError(e)

        # retrieve the tap indices for this ccd.
        tap_indices =  None
        try:
           tap_indices = self.ls4_ccd_map.get_tap_indices(ccd_location=ccd_location,\
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
            # the sub-images, all stacked together (the total row length is num_ccds*num_taps*num_pixels).
            # The number of rows is the same as the number of rows of each sub image.

            ccd_data = []
            for tap_index in tap_indices:
              x0 = tap_index * num_pixels
              x1 = x0 +  num_pixels
              y0 = 0
              y1 = y0 + num_lines
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
              x0 = (tap_index // num_taps) * num_pixels
              x1 = x0 +  num_pixels
              y0 + num_lines * j
              y1 = y0 + num_lines
              ccd_data.append(self.image_data[y0:y1, x0:x1])
              j += 1


        else:
            raise ValueError(f"Framemode {framemode} is not supported at this time.")

        return ccd_data
