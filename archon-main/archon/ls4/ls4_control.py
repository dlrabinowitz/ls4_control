# This file defines the LS4_Control class, which allows control of the LS4 
# camera through high-level commands to the Archon CCD controllers.

# The program implements basic commands to initialize, configure, and readout the 
# four synchronized Archon controllers that are interfaced to camera.
# Each controller reads out one quadrant of the array, consisting of 8 2K x 4K CCDs,
# each with two amplifiers wired to read the  left and right (1K x 4K ) halves.
#
# The 4 controllers share a common clock signal so that commands to prepare, expose, 
# and readout the 4 quadrants are executed simultaneously.

# Each controllers read the exposed images to their own internal memory buffer before 
# the data are ready to transfer to the computer host. The transfer of these data may 
# optionally occur while the controllers are exposing or reading out the next image.

# Four archon-config files (*.acf) must be prepared before running this script. These
# are initially created using the "archongui", an interactive program to create and tune 
# parameters and timing code for each controller. Generally, the acf files are identical,
# except for CCD-specific parameters associated with the respective CCD video outputs.

# Associated with each acf file is a json-formatted text file giving the name and location
# of each CCD in the associated quadrant of the array.

# The LS4_Control class imports python classes defined in the "ls4_control"
# distribution, which is built on top of the SDSS/archon on github.
# 
#
# See "test()" routine for a typical implementation
#

import sys
import os
import asyncio
import archon
from archon import log
import logging
import time
import argparse

from archon.ls4.ls4_sync import LS4_Sync
from archon.controller.ls4_logger import LS4_Logger   
from archon.controller.ls4_mainloop import Mainloop_Function as ML
from archon.ls4.ls4_conf import LS4_Conf     
from archon.ls4.ls4_camera import LS4_Camera
from archon.ls4.ls4_status import LS4_Status
from archon.tools import check_bool_value
from archon.ls4.ls4_exp_modes import *
from archon.ls4.ls4_mosaic import LS4_Mosaic
from archon.tools import get_obsdate
from archon.ls4.ls4_header import LS4_Header

class LS4_Control:

  def __init__(self,logger=None, ls4_conf_file=None,init_conf=None,parse_args=False):

     """ 
         If init_conf is specified, it is a dictionary to initialize conf. 
         If ls4_conf_file is provided, it is a json file that overwrites
         ors adds additional configuration parameters/
         If parse_args is True, parse the command line
         for additional configuration parameters.

         The order of initialization is
         (1) default
         (2) init_conf
         (3) ls4_conf_file
         (4) command_line args

     """

     self.ls4_logger=logger
     self.ls4_conf=None
     self.ls4_status=None
     error_msg = None

     # initialize configuration and ls4_logger if logger=None
     try:
       ls4_configurator = LS4_Conf(logger=logger,ls4_conf_file=ls4_conf_file, init_conf=init_conf, parse_args = parse_args)
       self.ls4_logger = ls4_configurator.logger
       self.ls4_conf = ls4_configurator.conf
     except Exception as e:
       error_msg="exception initializing configuration parameters: %s" %e

     if error_msg is None:
       self.info = self.ls4_logger.info
       self.debug= self.ls4_logger.debug
       self.warn = self.ls4_logger.warn
       self.error= self.ls4_logger.error
       self.critical= self.ls4_logger.critical

       # instantiate and update status
       self.ls4_status=LS4_Status()
       self.ls4_status.update({'ready':False,'state':'initializing',\
                             'error':False,'comment':'initializing'})

       # shortcuts
       self.exptime = self.ls4_conf['exptime']
       self.name_list = self.ls4_conf['name_list']
       self.ip_list = self.ls4_conf['ip_list']
       self.port_list = self.ls4_conf['port_list']
       self.bind_list = self.ls4_conf['bind_list']
       self.conf_path = self.ls4_conf['conf_path']
       self.acf_list = self.ls4_conf['acf_list']
       self.map_list = self.ls4_conf['map_list']
       self.num_exp = self.ls4_conf['num_exp']
       self.clear_time = self.ls4_conf['clear_time']
       self.leader_name = self.ls4_conf['leader']
       self.exp_incr = self.ls4_conf['exp_incr']
       self.exp_delay = self.ls4_conf['delay']
       self.shutter_mode = self.ls4_conf['shutter_mode']
       self.initial_reboot = self.ls4_conf['initial_reboot']
       self.num_controllers = len(self.name_list)
       self.num_enabled_controllers=len(self.ls4_conf['enable_list'])

       # evaluate bool expressions in ls4_conf (they could be bool or string values).
       self.save_images = check_bool_value(self.ls4_conf['save'],True)
       self.fake_controller = check_bool_value(self.ls4_conf['fake'],True)
       self.power_down = check_bool_value(self.ls4_conf['power_down'],True)
       self.sync_controllers = check_bool_value(self.ls4_conf['sync'],True)
       self.initial_clear= check_bool_value(self.ls4_conf['initial_clear'],True)
       self.initial_reboot= check_bool_value(self.ls4_conf['initial_reboot'],True)


       # init three instances of LS4_Header: 
       #  (1) self.extra_info_header records info added before
       #      the expose command is executed using the "header" command in ls4_commands.py
       #      (e.g. telescope position and status).
       #  (2) self.acquire_header records the contents of extra_info_header and any other info
       #      added to directly to acquire_header since the end of the previous acquisition.
       #  (3) self.fetch_header recorded the contents of acquire_header when acquisition ends. This
       #      is added to the fits headers when the fetched data are saved.

       self.extra_info_header = LS4_Header(ls4_logger=self.ls4_logger)
       self.acquire_header = LS4_Header(ls4_logger = self.ls4_logger)
       self.fetch_header = LS4_Header(ls4_logger = self.ls4_logger)


       #initialize list of empty configuration dictionaries, one for each named controller.
       #Also initialize list of instantiated LS4_Camera instances to Nones.

       self.ls4_list=[]
       self.ls4_conf_list=[]
       for _ in self.name_list:
           self.ls4_conf_list.append({})
           self.ls4_list.append(None)

       # initialize empty list of enabled instances of LS4_Camera
       self.enabled_cam_list=[]

     if error_msg is None:
       # if controllers are synced, verify the named lead controller is valid
       self.lead_index=None
       if self.sync_controllers:
         if self.leader_name not in self.name_list:
             error_msg = "leader_name must be in %s" % self.name_list
         elif self.leader_name not in self.ls4_conf['enable_list']:
             error_msg =  "lead controller %s is not in enabled list %s" %\
                    (leader_name,self.ls4_conf['enable_list'])
         else:
             self.lead_index = self.name_list.index(self.leader_name)
       else:
         self.lead_index=0

     if error_msg is None:
       idle_function = self.ls4_conf['idle_function']
       if idle_function == 'none':
          self.ls4_conf['idle_function'] = ML.NONE_FUNCTION
       elif idle_function == 'clear':
          self.ls4_conf['idle_function'] = ML.CLEAR_FUNCTION
       elif idle_function == 'flush':
          self.ls4_conf['idle_function'] = ML.FLUSH_FUNCTION
       else:
          error_msg = 'idle_function must be none,clear,or flush'
          
     if error_msg is not None:
       if self.ls4_logger is not None:
          self.ls4_logger.error(error_msg)
       raise RuntimeError(error_msg)

     # abort_flag is raised when self.abort() is called
     self.abort_flag=False

  @ property
  def status(self):
     return self.ls4_status.get()

  async def set_extra_header(self,info):
     error_msg = None

     if info is not None:
       try:
           await self.extra_info_header.set_header_info(conf=info)
       except Exception as e:
           error_msg="failed to update extra header: %s" %e

     self.debug("returning with error = %s" % str(error_msg))
     return error_msg

  async def initialize(self, reboot = False):

     """ initialize configuration parameters required to synchronize controller operations.
         Individual instances of LS4_Camera, one for each controller, are instantiated and
         initialized.

         Each instance controls the operation of the respective controller. Every camera operation
         is orchestrated through LS4_Control, which coordinates the collective actions of
         the controllers with synchronous calls to the LS4_Camera instances.

         If reboot is True, reboot the controllers before they are initialized.
     """
         

     if reboot or self.initial_reboot:
        reboot = True
        # only reboot on first initialization (unless reboot = True)
        self.initial_reboot = False

     self.info("########## %s: instantiating controllers with reboot = %s: %s" % \
            (get_obsdate(),reboot,self.name_list))

     # update local conf object for each controller with specific calues for fit-file prefix,
     # ip number, name, local_addr for socket io, archon config file, and ccd map file.


     # instantiate LS4_Sync , which creates parameters, lists, and 
     # synchronizing primitives and functions used to synchronize the
     # commands sent to the controllers. 

     self.info("########## %s: instantiating LS4_Sync for %d enabled controllers" % \
           (get_obsdate(),self.num_enabled_controllers))

     try:
       self.ls4_sync = LS4_Sync(num_synced_controllers = self.num_enabled_controllers,\
                         lead_index=self.lead_index,\
                         ls4_logger=self.ls4_logger)
     except Exception as e:
       error_msg = "Exception instantiating LS4_Sync: %s" % e
       self.error(error_msg)
       raise RuntimeError(error_msg)


     self.enabled_cam_list=[]
     for index in range(0,self.num_controllers):
         name=self.name_list[index]
         conf = self.ls4_conf_list[index]
         conf.update(self.ls4_conf)
         conf.update({'image_prefix':'%sC%d' % (self.ls4_conf['image_prefix'],index)})
         conf.update({'ip':self.ip_list[index]})
         conf.update({'name':name})
         conf.update({'local_addr':(self.bind_list[index],self.port_list[index])})
         conf.update({'acf_file':self.conf_path+"/"+self.acf_list[index]})
         conf.update({'map_file':self.conf_path+"/"+self.map_list[index]})

         if name not in self.ls4_conf['enable_list']:
            self.info("Skipping instantiation of controller %s, disabled" % name)
         else:
            try:
              self.ls4_list[index]=LS4_Camera(ls4_conf=conf,ls4_sync=self.ls4_sync,
                  command_args=self.ls4_sync.command_args,param_args=self.ls4_sync.param_args,
                  fake=self.fake_controller)
              self.enabled_cam_list.append(self.ls4_list[index])
            except Exception as e:
              error_msg = "Exception instantiating LS4_Camera for index %d: %s" %\
                     (index,e)
              self.error(error_msg)
              self.ls4_status.update({'error':True,'comment':error_msg})
              raise RuntimeError(error_msg)

     if self.ls4_list[self.lead_index] is None:
        error_msg = "lead controller %s was not enabled" % self.leader_name
        self.error(error_msg)
        self.ls4_status.update({'error':True,'comment':error_msg})
        raise RuntimeError(error_msg)

     if self.sync_controllers:
        self.hold_timing = True
        self.release_timing= False
     else:
        self.hold_timing = False
        self.release_timing = True

     self.info("########## %s: initializing controllers with reboot = %s" % (get_obsdate(),reboot))

     self.ls4_status.update({'ready':False,'state':'initializing','comment':'initializing'})

     try:
        await asyncio.gather(*(self.init_controller(ls4_cam,hold_timing=self.hold_timing, reboot=reboot)\
                for ls4_cam in self.ls4_list))
     except Exception as e:
        error_msg = "Exception initializing controllers: %s" % e 
        self.error(error_msg)
        self.ls4_status.update({'error':True,'comment':error_msg})
        raise RuntimeError(error_msg)


     self.ls4_list[self.lead_index].set_lead(True)

     sync_index=0
     for ls4_cam in self.enabled_cam_list:
        if ls4_cam.ls4_conf['name'] != self.leader_name:
           self.ls4_sync.add_controller(ls4_cam.ls4_controller,sync_index=sync_index)
           sync_index += 1
        else:
           self.ls4_sync.add_controller(ls4_cam.ls4_controller,sync_index=None)

     self.ls4_status.update({'ready':True,'state':'initialized','error':False,'comment':'initialized'})

  async def start(self):

     """ start the controller timing code. Normally this powers up each controller and
         puts them into auto-clear loops. 
     """

     error_msg = None

     self.ls4_status.update({'state':'starting','comment':'starting'})
     self.info("########## %s: starting controllers" % get_obsdate())

     # When synchronizing controllers, don't start the timing code until 
     # all the controllers have been separately started 
     if self.sync_controllers:
        release_timing= False

     # otherwise they can start their timing codes asynchronously
     else:
        release_timing = True

     try:
       await asyncio.gather(*(self.start_controller(ls4_cam,release_timing=self.release_timing)\
                          for ls4_cam in self.ls4_list))
     except Exception as e:
       error_msg = "Exception starting controllers with release_timing = %s: %s" % \
            (release_timing,e)
       self.error(error_msg)
       raise RuntimeError(error_msg)

     if self.sync_controllers:
       self.info("########## %s: syncing controllers" % get_obsdate())
       await asyncio.gather(*(self.sync_controller(ls4_cam) for ls4_cam in self.enabled_cam_list))
       await self.set_sync(sync=True,test=True)

     if self.initial_clear:
       self.info("########## %s: clearing CCDs" % get_obsdate())
       await self.clear(self.clear_time)

     self.image_count=self.ls4_conf['init_count']

     self.ls4_status.update({'state':'started','comment':'started'})
     await self.update_cam_status()

     self.info("########## %s: success starting controllers" % get_obsdate())

  async def stop(self, stop_timing=True, power_down=True):

      """ stop the controller timing code. This also powers down each controller.
      """

      self.ls4_status.update({'state':'stopping','comment':'stopping'})
      try:
        await self.update_cam_status()
        self.ls4_logger.info("########## %s: stopping controllers" % get_obsdate())
        await asyncio.gather(*(self.stop_controller(ls4=ls4_cam, power_down=power_down) \
                          for ls4_cam in self.enabled_cam_list))
      except Exception as e:
        error_msg = "exception stopping controller: %s" % e
        self.error(error_msg)
      self.ls4_status.update({'state':'stopped','comment':'stopped'})
      #await self.update_cam_status()

  async def update_cam_status(self):
      """ update all cam status keywords beginning with BIT_ """

      cam_status = {}
      for ls4_cam in self.enabled_cam_list:
          status = await ls4_cam.get_status()
          if status is not None:
            for key in status:
             if "BIT_" in key:
               key1=key.replace("BIT_","")
               if key1 not in cam_status:
                 cam_status[key1]=""
               cam_status[key1] += str(status[key])

      self.ls4_status.update(cam_status)


  def get_image_list(self):
      """ get list of images from previously saved exposure """

      image_list = []
      for ls4_cam in self.enabled_cam_list:
         image_list += ls4_cam.image_list
      return image_list

  async def clear(self,clear_time=0.0):
      """ start autoclearing, wait clear_time, stop autoclearing """
 
      self.info("########## %s: start clearing for %7.3f sec" % (get_obsdate(),clear_time))
      await self.enable_autoclear()
      t_start = time.time()
      done = False
      dt = 0.0
      while (not done) and (not self.abort_flag):
         dt = time.time() - t_start
         if dt > clear_time:
            done = True
         else:
            await asyncio.sleep(0.1)

      if self.abort_flag:
         self.warn("clear aborted after %7.3f sec" % dt)

      await self.disable_autoclear()

      self.info("########## %s: done clearing for %7.3f sec" % (get_obsdate(),clear_time))

  async def enable_autoclear(self):
      """ enable autoclear option on controllers and return """
      self.info("########## %s: enabling autoclear " % get_obsdate())
      await asyncio.gather(*(self.start_autoclear(ls4_cam) for ls4_cam in self.ls4_list))
      self.debug("########## %s: done enabling autoclear " % get_obsdate())

  async def disable_autoclear(self):
      """ disable autoclear option on controllers and return """
      self.info("########## %s: disabling autoclear " % get_obsdate())
      await asyncio.gather(*(self.stop_autoclear(ls4_cam) for ls4_cam in self.ls4_list))
      self.debug("########## %s: done disabling autoclear " % get_obsdate())


  async def enable_autoflush(self):
      """ enable autoflush option on controllers and return """
      self.info("########## %s: enabling autoflush " % get_obsdate())
      await asyncio.gather(*(self.start_autoflush(ls4_cam) for ls4_cam in self.ls4_list))
      self.debug("########## %s: done enabling autoflush " % get_obsdate())

  async def disable_autoflush(self):
      """ disable autoflush option on controllers and return """
      self.info("########## %s: disabling autoflush " % get_obsdate())
      await asyncio.gather(*(self.stop_autoflush(ls4_cam) for ls4_cam in self.ls4_list))
      self.debug("########## %s: done disabling autoflush " % get_obsdate())

  async def power_up_biases(self):
      """ power up CCD biases """

      self.info("########## %s: powering up CCD biases" % get_obsdate())
      await asyncio.gather(*(self.power_up_controller(ls4_cam) for ls4_cam in self.ls4_list))
      self.debug("########## %s: done powering up CCD biases" % get_obsdate())

  async def power_down_biases(self):
      """ power up CCD biases """

      self.info("########## %s: powering down CCD biases" % get_obsdate())
      await asyncio.gather(*(self.power_down_controller(ls4_cam) for ls4_cam in self.ls4_list))
      self.debug("########## %s: done powering down CCD biases" % get_obsdate())

  async def enable_vsub(self):
      """ enable Vsub CCD bias """

      error_msg = None
      results = [None]
      self.info("########## %s: enabling Vsub bias" % get_obsdate())
      results = await asyncio.gather(*(self.enable_vsub_bias(ls4_cam) for ls4_cam in self.ls4_list))
      self.debug("########## %s: done enabling Vsub bias" % get_obsdate())

      index = 0
      for msg in results:
         if msg is not None:
            if error_msg is None:
               error_msg = "Failed to enable bias for controller %d " % index
            else:
               error_msg += "%d " % index
         index += 1

      if error_msg is not None:
         self.error(error_msg)
      return error_msg

  async def disable_vsub(self):
      """ disable Vsub CCD bias """

      error_msg = None
      results = [None]
      self.info("########## %s: disabling Vsub bias" % get_obsdate())
      results = await asyncio.gather(*(self.disable_vsub_bias(ls4_cam) for ls4_cam in self.ls4_list))
      self.debug("########## %s: done disabling Vsub bias" % get_obsdate())

      index = 0
      for msg in results:
         if msg is not None:
            if error_msg is None:
               error_msg = "Failed to disable bias for controller %d " % index
            else:
               error_msg += "%d " % index
         index += 1

      if error_msg is not None:
         self.error(error_msg)
      return error_msg


  async def erase(self):
      """ Run erase procedure on CCDs """

      self.info("########## %s: running erase procedure" % get_obsdate())
      await asyncio.gather(*(self.erase_ccds(ls4_cam) for ls4_cam in self.ls4_list))
      self.debug("########## %s: done running erase procedure" % get_obsdate())


  async def purge(self,fast=False):
      """ Run purge procedure on CCDs """

      self.info("########## %s: running purge procedure" % get_obsdate())
      await asyncio.gather(*(self.purge_ccds(ls4=ls4_cam,fast=fast) for ls4_cam in self.ls4_list))
      self.debug("########## %s: done running purge procedure" % get_obsdate())


  async def flush(self,fast=False,flushcount=1):
      """ Run flush procedure on CCDs """

      self.info("########## %s: running flush procedure" % get_obsdate())
      await asyncio.gather(*(self.flush_ccds(ls4=ls4_cam,fast=fast,flushcount=flushcount)\
                               for ls4_cam in self.ls4_list))
      self.debug("########## %s: done running flush procedure" % get_obsdate())


  async def clean(self,erase=False, n_cycles=10,flushcount=1,fast=False):
      """ Run clean procedure on CCDs """

      self.info("########## %s: running clean procedure" % get_obsdate())
      await asyncio.gather(*(self.clean_ccds(ls4=ls4_cam,erase=erase,\
                              n_cycles=n_cycles,flushcount=flushcount,fast=fast)\
                               for ls4_cam in self.ls4_list))
      self.debug("########## %s: done running clean procedure" % get_obsdate())


  async def abort(self,readout=True):
      """ abort any ongoing exposures and readout if readout is True """

      error_msg =  None
      self.abort_flag = True

      self.info("########## %s: aborting exposure" % get_obsdate())
      results = await asyncio.gather(*(self.abort_exposure(ls4=ls4_cam,readout=readout)\
                               for ls4_cam in self.ls4_list))
      self.debug("########## %s: done aborting exposure" % get_obsdate())

      for r in results:
         if r is not None:
            if error_msg is None:
               error_msg = r
            else:
               error_msg += " %s" % r

      if error_msg is not None:
         self.error(error_msg)
     
      return error_msg

  async def clear_abort(self):
      """ clear abort_flag """
      self.abort_flag = False


  async def start_autoclear(self,ls4=None):
      """ start the autoclear on the controller associated with  the instance of LS4_Camera specified by ls4.
      """
      error_msg = None
      if ls4 is not None:
        ls4.debug("start autoclearing")
        await ls4.start_autoclear()

  async def stop_autoclear(self,ls4=None):
      """ stop  the autoclear on the controller associated with the instance of LS4_Camera specified by ls4.
      """
      if ls4 is not None:
        ls4.debug("stop autoclearing")
        await ls4.stop_autoclear()

  async def start_autoflush(self,ls4=None):
      """ start the autoflush on the controller associated with  the instance of LS4_Camera specified by ls4.
      """
      error_msg = None
      if ls4 is not None:
        ls4.debug("start autoflushing")
        await ls4.start_autoflush()

  async def stop_autoflush(self,ls4=None):
      """ stop  the autoflush on the controller associated with the instance of LS4_Camera specified by ls4.
      """
      if ls4 is not None:
        ls4.debug("stop autoflushing")
        await ls4.stop_autoflush()


  async def start_controller(self,ls4=None, release_timing=False):
      """ start controller for instance of LS4_Camera specified by ls4.
          If release_timing is True, start the timing routine on the controller.
      """

      error_msg = None
      if ls4 is not None:

        error_msg = None
        try:
          await ls4.start_controller(release_timing=release_timing)
        except Exception as e:
          error_msg = "exception starting controller"

        if error_msg is None:
          ls4.debug("checking voltages")
          try:
            status = await ls4.get_status()
            in_range  = await ls4.check_voltages(status=status)
          except Exception as e:
            error_msg = "exception checking voltages: %s" %e

        if (error_msg is None) and (not in_range):
          ls4.warn("voltages out of range on first check. Checking again ...")
          await asyncio.sleep(1)
          try:
            status = await ls4.get_status()
            in_range = await ls4.check_voltages(status=status)
          except Exception as e:
            error_msg = "exception checking voltages 2nd try"

        if error_msg is not None:
          self.error(error_msg)
        assert error_msg is None, error_msg

  async def init_controller(self,ls4=None,hold_timing=False, reboot = False):
      """ initialize the controller associated with the instance of LS4_Camera specified by ls4.
          If hold_time is True, do not run the timing code. 
          If reboot is True, reboot the controller before initializing
      """
      if ls4 is not None:
        ls4.debug("initializing with reboot = %s" % reboot )
        await ls4.init_controller(hold_timing=hold_timing,reboot=reboot)

  async def reset(self,ls4=None,release_timing=False):
      """ reset the controller associated with the instance of LS4_Camera specified by ls4.
          If release_time is True, run the timing code. 
      """
      if ls4 is not None:
        ls4.debug("resetting")
        await ls4.reset(release_timing=release_timing)


  async def sync_controller(self,ls4=None):
      """ Synchronize the controller associated with the instance of LS4_Camera specified by ls4.
          This will synchronize the controller to the lead controller if set_sync
          was previously called with sync=True.
      """
      if ls4 is not None:
        await ls4.release_timing()

  async def set_sync(self,sync=True,test=False):
      """ Set the option for syncing on the instance of LS4_Camera specified by ls4.
      """

      assert self.ls4_sync is not None,"ls4_sync is not instantiated"
      await self.ls4_sync.set_sync(sync)
      if test:
        await self.ls4_sync.test_sync()

  async def stop_controller(self,ls4=None,power_down=True):
      """ Stop the controller associated with the instance of LS4_Camera specified by ls4.
          If power_down = True, power down the controller before the controller
          is stopped. Stopping controller deletes the instance of the LS4_Camera
          and the associated controller.
      """
      if ls4 is not None:
        ls4.debug("stopping controller: power_down = %s" % power_down)
        await ls4.stop_controller(power_down)

  async def power_up_controller(self,ls4=None):
      """ power up the biases of the controller associated with the instance of 
          LS4_Camera specified by ls4.
      """
      if ls4 is not None:
        ls4.debug("powering up controller biases")
        await ls4.power_up()

  async def power_down_controller(self,ls4=None):
      """ power down the biases of the controller associated with the instance of 
          LS4_Camera specified by ls4.
      """
      if ls4 is not None:
        ls4.debug("powering down controller biases")
        await ls4.power_down()


  async def enable_vsub_bias(self,ls4=None):
      """ enable the Vsub bias of the controller associated with the instance of 
          LS4_Camera specified by ls4. When enabled, the Vsub bias will power up/down
          along with all the other biases when power_up/down_controller is executed. 
      """
      if ls4 is not None:
        ls4.debug("enabling Vsub bias")
        return await ls4.enable_vsub()

  async def disable_vsub_bias(self,ls4=None):
      """ disable the Vsub bias of the controller associated with the instance of 
          LS4_Camera specified by ls4. When disabled, the Vsub bias will remained powered
          off when al the other biases are powered up or down.
      """
      if ls4 is not None:
        ls4.debug("disabling Vsub bias")
        return await ls4.disable_vsub()

  async def erase_ccds(self,ls4=None):
      """ Run the erase procedure on the CCDs associated with the instance of 
          LS4_Camera specified by ls4. 
      """
      if ls4 is not None:
        ls4.debug("erasing CCDs")
        return await ls4.erase()

  async def purge_ccds(self,ls4=None,fast=False):
      """ Run the purge procedure on the CCDs associated with the instance of 
          LS4_Camera specified by ls4. If fast = True, use the fast mode. 
      """
      if ls4 is not None:
        ls4.debug("purging CCDs")
        return await ls4.purge(fast=fast)

  async def flush_ccds(self,ls4=None,fast=False,flushcount=1):
      """ Run the flush procedure on the CCDs associated with the instance of 
          LS4_Camera specified by ls4. If fast = True, use the fast mode. The
          flush procedure repeats for multiple cycles specified by flushcount.
      """
      if ls4 is not None:
        ls4.debug("flushing CCDs")
        return await ls4.flush(fast=fast,flushcount=flushcount)

  async def clean_ccds(self,ls4=None,erase=False, n_cycles=10,flushcount=1,fast=False):
      """ Run the clean procedure on the CCDs associated with the instance of 
          LS4_Camera specified by ls4. If erase=True, run the erase procedure
          first. Then run the purge procedure for n_cycles cycles. Finish
          by runnunf the flush procedure for flushcount iterations.
      """
      if ls4 is not None:
        ls4.debug("cleaning CCDs")
        return await ls4.clean(erase=erase,n_cycles=n_cycles,flushcount=flushcount,fast=fast)


  async def abort_exposure(self,ls4=None,readout = True):
      """ abort any on-going exposure. 
          if readout is False, abort the readout also.
      """
      if ls4 is not None:
        return await ls4.abort_exposure(readout)


  async def exp_sequence(self,exptime=None,suffix="",ls4=None,ls4_conf=None,\
            acquire=False, fetch=False, save=False, concurrent=False, enable_shutter=False):

      """ For the instance of LS4_Camera specified by ls4,
          acquire a new exposure and/or fetch an exposure, with the following 4 modes
          depending on acquire/fetch/concurrent:

            True/False/False: exposure and readout the image to controller memory, 
                             but don't fetch the data from controller.

            False/True/False: fetch the last acquired image from the controller,
                              but don't expose and readout a new image (in this
                              thread, or any concurrent thread)

            True/True/False: expose a new image, read it out to controller memory,
                             and only then fetch the data

            False/True/False: fetch the previously acquired and read out image. This assumes
                             that there is no concurrent thread that is reading out a new 
                             exposure.

            True/True/True: fetch the previously acquired image, while simultaneously
                             exposing a new image and reading it out to controller memory
                             in a concurrent thread.
                                  
                                  
          Notes:

          1.  the controllers have three image buffers. As long as the time to fetch
          and optionally save an image is less than the time to readout each new image,
          then the fetching and acquiring can proceed simultaneously.

          2. Three header dictionaries (extra_info_header, acquire_header, fetch_header)
          are used to record status data from the telescope. The data are transferred from one buffer 
          to another in stages timed to allow concurrent telescope motion, camera readout,
          and data fetching.

          The staging :

             move telescope
             update extra_info_header
             Copy extra_info_header to aquire_header
             start new acquisition
             Copy aquire_header to fetch_header
             start fetching and saving
             use fetch_header to update FITS headers

          The timing:
         
              main thread:
                (1) Wait for telescope to settle at next pointing.
                    Update extra_info_header with telescope status.
                    This may occur while a previous exposure is being readout,
                    and an even earlier exposure is being fetched and saved.

                (2) Wait for any ongoing acquisition and fetch threads to exit.
                    Copy extra_info_header to acquire_header.
                    Clear extra_info_header.
                    Start new acquisition thread.
                    The acquire_header will not change until the next acquisition ends.
                     
                (3) If concurrent acquire/fetch:
                    Copy fetch_header to temporary buffer.
                    Clear fetch_header.
                    Start fetch thread (with temporary buffer as argument)
         
                (4) Wait for acquisition thread to start reading out CCD.
                    Start moving telescope to next pointing.
         
                (5) Wait for acquisition thread (and fetch thread if concurrent) to exit.
                    Copy acquire_header to fetch_header.
                    Clear acquire_header.
                    The fetch header will not change until the next fetch starts
         
                (6) If sequential acquire/fetch:
                      Copy fetch_header to temporary buffer.
                      Clear fetch_header.
                      Start new fetch thread (with temporary buffer as argument)
                      Wait for fetch thread to exit.
         
            
         

      """


      assert ls4 is not None, "ls4 controller uninitialized"
      assert isinstance(ls4,(LS4_Camera)),"ls4 is not an instance of LS4_Camera"

      

      error_msg = None


      if not (acquire or fetch):
        error_msg = "must acquire and/or fetch"
        self.error_msg
      else:
        if exptime is None:
           exptime = ls4_conf['exptime']
        else:
           ls4_conf['exptime']=exptime

        image_prefix = ls4_conf['image_prefix']
        output_image = ls4_conf['data_path']+"/"+image_prefix + suffix

      if fetch and (error_msg is None):
        await self.fetch_header.initialize()
        h  = await self.acquire_header.header
        await self.fetch_header.set_header_info(conf=h)

      if acquire and (error_msg is None):
        try:
          status = await ls4.get_status()
          assert await ls4.check_voltages(status=status), "voltages out of range"
        except Exception as e:
          error_msg = "Exception checking voltages: %s" %e
          self.error(error_msg)

        # copy extra_info_header to acquire_header
        self.debug("copying extra_info_header to acquire_header")
        h = await self.extra_info_header.header
        await self.acquire_header.initialize()
        await self.acquire_header.set_header_info(conf=h)

        await self.extra_info_header.initialize()

      # acquire and fetch at the same time
      if acquire and fetch and concurrent and (error_msg is None):
        self.debug("copying fetch_header to h")
        h = await self.fetch_header.header
        try:
          await asyncio.gather(\
                  ls4.acquire(exptime=exptime,output_image=output_image,concurrent=concurrent,\
                         acquire=True,fetch=False,save=False,enable_shutter=enable_shutter,\
                         header=None),
                  ls4.acquire(exptime=exptime,output_image=output_image,concurrent=concurrent,
                         acquire=False, fetch=True,save=save,enable_shutter=enable_shutter,
                         header=h))
        except Exception as e:
           error_msg = "image %s: exception acquiring and fetching at same time: %s" % (output_image,e)
           self.error(error_msg)

        await self.fetch_header.initialize()
        h  = await self.acquire_header.header
        await self.fetch_header.set_header_info(conf=h)

      # acquire and/or fetch but not at the same time
      elif (acquire or fetch) and (not concurrent) and (error_msg is None):
        if acquire:
          try: 
             await ls4.acquire(exptime=exptime,output_image=output_image,acquire=True,concurrent=concurrent,\
                              fetch=False,save=False,enable_shutter=enable_shutter,header=None)
          except Exception as e:
             error_msg = "image %s: exception acquiring and fetching sequentially: %s" % (output_image,e)
             self.error(error_msg)

        await self.fetch_header.initialize()
        h = await self.acquire_header.header
        await self.fetch_header.set_header_info(conf=h)

        if fetch and (error_msg is None):
          try: 
             await ls4.acquire(exptime=exptime,output_image=output_image,acquire=False,concurrent=concurrent,\
                    fetch=True,save=save,header=h)
          except Exception as e:
             error_msg = "image: %s: exception saving fetched data: %s" %\
                           (output_image,e)
             self.error(error_msg)

      elif error_msg is None:
         error_msg = "unexpected combination of acquire/fetch/concurrent: %s %s %s" %\
                       (acquire,fetch,concurrent)
         self.error(error_msg)

      assert error_msg is None, error_msg

  async def expose(self, exptime=0.0, exp_num = 0, enable_shutter = True,  exp_mode=exp_mode_single, fileroot=None):

      error_msg = None

      if exp_mode == exp_mode_last:
        try:
          assert exp_num>0, "exp_mode is exp_mode_last but no previous exposure"
        except Exception as e:
          error_msg = e

     

      if (fileroot is not None) and (error_msg is None):
        self.info("setting file root to %s" % fileroot)
        self.ls4_conf['image_prefix']=fileroot
        index=0
        for ls4 in self.ls4_list:
            f = "%sC%d" % (self.ls4_conf['image_prefix'],index)
            ls4.update_conf('image_prefix',f)
            index += 1

      if (error_msg is None) and self.sync_controllers:
        self.info("setting sync")
        try:
          await self.set_sync(sync=True,test=True)
        except Exception as e:
          error_msg ="########## Exception syncing controllers: %s" %e

      if (error_msg is None):

        self.info("setting image suffix")
        image_suffix = "_%05d"%exp_num + ".fits"

        if exp_mode == exp_mode_first:
          self.info("########## %s: acquiring but not fetching  exposure  %d" % \
                (get_obsdate(),exp_num))
        elif exp_mode == exp_mode_next:
          self.info("########## %s: acquiring exposure %d while fetching exposure %d" %\
                (get_obsdate(),exp_num, exp_num-1))
        elif exp_mode == exp_mode_last:
          self.info("########## %s: fetching last exposure %d" % \
                (get_obsdate(),exp_num))
        elif exp_mode == exp_mode_single:
          self.info("########## %s: acquiring and fetching exposure %d" % \
                (get_obsdate(),exp_num))
        else:
          error_msg = "########## %s: unrecognized exposure mode [%s] for exposure %d" %\
                (get_obsdate(),exp_nu)

      if (error_msg is None) and not exp_mode == exp_mode_last:
        if self.sync_controllers:
          self.info("setting sync")
          try:
             await self.set_sync(True)
          except Exception as e:
            error_msg = "Exception syncing controllers before new exposure: %s" %e
         
      if error_msg is None:
         self.info("updating status")
         self.ls4_status.update({'state':'exposing','comment':'expo_mode %s' % exp_mode})

      if (error_msg is None) and exp_mode == exp_mode_first:
        self.info("awaiting exp_sequence threads for exp_mode_first")
        try:
          await asyncio.gather(*(self.exp_sequence(exptime=exptime,ls4=self.ls4_list[index],\
                       ls4_conf= self.ls4_conf_list[index],acquire=True,suffix=image_suffix,\
                       fetch=False,concurrent=False,save=False,enable_shutter=enable_shutter) \
                       for index in range(0,self.num_controllers)))
           
          self.debug("done awaiting exp_sequence threads")
        except Exception as e:
          error_msg = "Exception executing exp_sequence with acquire/fetch/concurrent = True/False/False: %s" % e


      elif (error_msg is None) and exp_mode == exp_mode_next:
        self.info("awaiting exp_sequence threads for exp_mode_next")
        try:
          await asyncio.gather(*(self.exp_sequence(exptime=exptime,ls4=self.ls4_list[index],\
                       ls4_conf= self.ls4_conf_list[index],acquire=True,suffix=image_suffix,\
                       fetch=True,concurrent=True,save=self.save_images,enable_shutter=enable_shutter) \
                       for index in range(0,self.num_controllers)))
          self.debug("done awaiting exp_sequence threads")
           
        except Exception as e:
          error_msg = "Exception executing exp_sequence with acquire/fetch/concurrent = True/True/True: %s" % e

      elif (error_msg is None) and exp_mode == exp_mode_last:
        self.info("awaiting exp_sequence threads for exp_mode_last")
        try:
          await asyncio.gather(*(self.exp_sequence(exptime=exptime,ls4=self.ls4_list[index],\
                       ls4_conf= self.ls4_conf_list[index],acquire=False,suffix=image_suffix,\
                       fetch=True,concurrent=False,save=self.save_images,enable_shutter=enable_shutter) \
                       for index in range(0,self.num_controllers)))
          self.debug("done awaiting exp_sequence threads")

        except Exception as e:
          error_msg = "Exception executing exp_sequence with acquire/fetch/concurrent = False/True/False: %s" % e

      elif (error_msg is None) and exp_mode == exp_mode_single:
        # acquire (expose/readout) and then fetch immediately after the readout ends
        # NOTE : Why can't exp_sequence handle the acquisition, wait, and then fetch ?
        self.info("awaiting exp_sequence threads for exp_mode_single with fetch=False,save=False")
        try:
          await asyncio.gather(*(self.exp_sequence(exptime=exptime,ls4=self.ls4_list[index],\
                         ls4_conf= self.ls4_conf_list[index],acquire=True,suffix=image_suffix,\
                         fetch=False,concurrent=False,save=False, enable_shutter=enable_shutter) \
                         for index in range(0,self.num_controllers)))
          self.debug("done awaiting exp_sequence threads")
        except Exception as e:
          error_msg = "Exception executing exp_sequence with acquire/fetch/concurrent = True/False/False: %s" % e
             
        if (error_msg is None):
          if self.sync_controllers:
            self.info("setting sync")
            try:
             await self.set_sync(False)
            except Exception as e:
              error_msg = "Exception unsyncing controllers after acquire before fetch: %s" %e
         
        if (error_msg is None):
          self.info("awaiting exp_sequence threads for exp_mode_single with fetch=True,save=%s" % self.save_images)
          try:
            await asyncio.gather(*(self.exp_sequence(exptime=exptime,ls4=self.ls4_list[index],\
                       ls4_conf= self.ls4_conf_list[index],acquire=False,suffix=image_suffix,\
                       fetch=True,concurrent=False,save=self.save_images,enable_shutter=enable_shutter) \
                       for index in range(0,self.num_controllers)))
            self.debug("done awaiting exp_sequence threads")
          except Exception as e:
            error_msg = "Exception executing exp_sequence with acquire/fetch/concurrent = False/True/False: %s" % e
 
      if error_msg is not None:
         self.info("error occurred")
         self.error("########## %s: %s" % (get_obsdate(),error_msg))
      else:
         if exp_mode != exp_mode_last:
            self.image_count += 1
 
      if error_msg is None:
         self.ls4_status.update({'state':'done exposing'})
      else:
         self.ls4_status.update({'state':'done exposing','error':True,'comment':error_msg})

      self.debug("returning")

      return error_msg
         
  """   
  async def close(self):

      if self.sync_controller:
        await self.ls4_sync.set_sync(False)


      if self.power_down:
          self.info("########## %s: stop autoclearing" % get_obsdate())
          await asyncio.gather(*(self.stop_autoclear(ls4_cam) for ls4_cam in self.ls4_list))

      self.info("########## %s: stopping controllers" % get_obsdate())
      await asyncio.gather(self.stop_controller(self.ls4_list[0],self.power_down),\
                           self.stop_controller(self.ls4_list[1],self.power_down),\
                           self.stop_controller(self.ls4_list[2],self.power_down),\
                           self.stop_controller(self.ls4_list[3],self.power_down))


      self.info("########## %s: exiting" % get_obsdate())
  """   

if __name__ == "__main__":

 async def go():

   error_msg = None

   try:
     ls4_ctrl = LS4_Control(parse_args=True)
   except Exception as e:
     error_msg = "failed to instantiated LS4_Control: %s" % e

   if error_msg is None:
       ls4_ctrl.info("initializing camera")
       try:
         await ls4_ctrl.initialize()
       except Exception as e:
         error_msg="failed to initialize LS4_Control: %s" % e
         ls4_ctrl.error(error_msg)


   if error_msg is None:
       ls4_ctrl.info("starting camera")
       try:
         await ls4_ctrl.start()
       except Exception as e:
         error_msg="failed to initialize LS4_Control: %s" % e
         ls4_ctrl.error(error_msg)


   exptime = ls4_ctrl.exptime

   last_exp_num = None
   if error_msg is None:
       exp_num_start = ls4_ctrl.image_count
       exp_num_end = exp_num_start + ls4_ctrl.num_exp
       for exp_num in range(exp_num_start, exp_num_end):
         ls4_ctrl.info("%s: taking exposure %d of %d" % (get_obsdate(),exp_num,ls4_ctrl.num_exp))
         if exp_num == 0:
           exp_mode = exp_mode_first
         else:
           exp_mode = exp_mode_next
         try:
           await ls4_ctrl.expose(exptime=exptime, exp_num=exp_num, enable_shutter = True, exp_mode=exp_mode)
         except Exception as e:
           error_msg = "exception taking exposure %d: %s" % (exp_num,e)
           break
         last_exp_num = exp_num

       if (error_msg is None) and (exp_mode != exp_mode_single) and (last_exp_num is not None):
         exp_num = last_exp_num
         try:
           await ls4_ctrl.expose(exptime=0.25, exp_num=exp_num, enable_shutter = True, exp_mode='last')
         except Exception as e:
           error_msg = "exception reading out last exposure %d: %s" % (exp_num,e)


   if error_msg is None:
       ls4_ctrl.info("starting autoclear")
       try:
         await ls4_ctrl.start_autoclear()
       except Exception as e:
         error_msg = "exception starting autoclear: %s" %e

   if error_msg is None:
       ls4_ctrl.info("stopping ls4_ctrl")
       try:
         await ls4_ctrl.stop(power_down=ls4_ctrl.power_down)
       except Exception as e:
         error_msg = "exception stopping ls4_control: %s" %e

   if error_msg is not None:
      ls4_ctrl.error(error_msg)

   ls4_ctrl.info("exiting")

 asyncio.run(go())
