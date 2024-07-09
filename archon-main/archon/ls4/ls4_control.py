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
from archon.ls4.ls4_camera import LS4_Camera
from archon.ls4.ls4_exp_modes import *
    

class LS4_Status():

    def __init__(self):
        self.status={}

    def update(self,s=None):
        if s is not None:
           self.status.update(s)

    def get(self):
        return self.status

    def clear(self):
        self.status={}

class LS4_Control():

    #exp_mode_single = 'single'
    #exp_mode_first  = 'first'
    #exp_mode_next   = 'next'
    #exp_mode_last   = 'last'
    #exp_modes = {\
    #      exp_mode_first:{'acquire':True,'fetch':False,'wait':True},\
    #      exp_mode_next:{'acquire':True,'fetch':True,'wait':False},\
    #      exp_mode_single:{'acquire':True,'fetch':True,'wait':True},\
    #      exp_mode_last:{'acquire':False,'fetch':True,'wait':True},\
    #     }

    def __init__(self,ls4_conf=None):

       """ initialize house keeping parameters and various lists that can be accessed
           across parallel threads. Also initialize separate instances of LS4_Camera, one
           for each controller
       """

       
       self.ls4_logger = LS4_Logger(name="LS4_Ctrl")

       # self.ls4_conf is the main register for configuration parameters. Default values
       # are added, and then updated from the ls4_conf argument to __init__.
       # Multiple copies are then made, one for each control, so that controller-specific
       # configuration and status updates can be stored separately.

       # initialize self.ls4_conf with defaults
       self.ls4_conf = self.init_ls4_conf()

       # instantiate and update status
       self.ls4_status=LS4_Status()
       self.ls4_status.update({'ready':False,'state':'initializing','error':False,'comment':'initializing'})


       # list name of critical parameters that must be described by self.ls4_conf

       critical_params = ['ip_list','bind_list','conf_path','data_path',\
                          'acf_list','map_list','flush_time','image_prefix',\
                          'leader','port_list','sync','fake',
                          'ctrl_names','enable_list','init_count']

       # verify that critical parameters are defined
       for key in critical_params:
           assert key in ls4_conf,"critical parameter %s missing from ls4_conf" % key


       # handy copies of parameter values and list of parameter values
       self.leader_name = ls4_conf['leader']
       self.ip_list = ls4_conf['ip_list']
       self.port_list = ls4_conf['port_list']
       self.bind_list = ls4_conf['bind_list']
       self.conf_path = ls4_conf['conf_path']
       self.acf_list = ls4_conf['acf_list']
       self.map_list = ls4_conf['map_list']
       self.flush_time = ls4_conf['flush_time']
       self.ctrl_names=ls4_conf['ctrl_names']
       self.image_prefix = ls4_conf['image_prefix']

       # update self.ls4_conf with entries from ls4_conf argument
       if ls4_conf is not None:
         self.ls4_conf.update(ls4_conf)

       # update number of controllers
       self.num_controllers = len(self.port_list)

       # create lists to store instances of LS4_Camera and copies of ls4_conf
       self.ls4_list=[]
       self.ls4_conf_list=[]
       for _ in range(0,self.num_controllers):
         self.ls4_list += [None]
         self.ls4_conf_list += [{}]

       # initialize empty list of enabled instances of LS4_Camera
       self.enabled_cam_list=[]


       self.sync_controllers = None 
       if ls4_conf['sync'] not in ['True','TRUE','T','true',True]:
          self.sync_controllers = False
       else:
          self.sync_controllers = True

       # ls4_sync is instantiated by instantiate_cameras
       self.ls4_sync = None

       # If syncing controllers, check again the name of the lead 
       # controller is  one of the declared controller names and that it
       # is enabled. Then  update the value for the lead index
       #
       if self.sync_controllers:
         assert self.leader_name in self.ctrl_names, \
              "leader_name [%s] not in ctrl name list[%s]" %\
              (self.leader_name,str(self.ctrl_names))

         assert self.leader_name in ls4_conf['enable_list'], \
                "lead controller %s is not enabled" % self.leader_name
         self.lead_index = self.ctrl_names.index(self.leader_name)

       # are we saving images to disk ?
       self.save_images = None
       if ls4_conf['save'] not in ['True','TRUE','T','true',True]:
          self.save_images = False
       else:
          self.save_images = True

       # are we faking the controller ?
       self.fake_controller = None
       if ls4_conf['fake'] in ['True','TRUE','T','true',True]:
          self.fake_controller = True
       else:
          self.fake_controller = False

       # are we powering down the controller when we exit ?
       self.power_down=None
       if ls4_conf['power_down'] not in ['True','TRUE','T','true',True]:
          self.power_down = False
       else:
          self.power_down=True

       self.ls4_logger.info("########## %s: instantiating cameras" % self.get_obsdate())
 
       self.instantiate_cameras()

       assert self.ls4_list[self.lead_index] is not None, "leader %s was not enabled" % self.leader_name

       self.image_count=ls4_conf['init_count']

       # space for extra header info
       self.header_info={}

    async def reset(self):
       
       self.ls4_logger.debug("delete old instances of LS4_Camera in ls4_list")
       for ls4 in self.ls4_list:
          if ls4 is not None:
             try:
                await ls4.reset_camera(sync_flag=False)
             except Exception as e:
                self.ls4_logger.warn("Exception resetting camera %s before re-instantiating: %s" % (ls4.name,e))

             try:
               del ls4
             except Exception as e:
               self.ls4_logger.warn("Exception deleting instance of camera %s before re-instantiating: %s" % (ls4.name,e))


       self.ls4_logger.debug("creating new instances of LS4_Camera")
       try:
         self.instantiate_cameras()
       except Exception as e:
         error_msg = "Excepetion instantiating cameras: %s" % e
         raise RuntimeError(error_msg)

    def set_extra_header(self,*kw_dict):

       """ given kw:arg dictionary, update the extra header info in
           each instance of LS4_Camera in self.ls4_list

           If *kw_dict is an empty dictionary, clear the extra_header
           info in each instance
       """

       for ls4 in self.ls4_list:
          if ls4 is not None:
             if len(*kw_dict) == 0:
               ls4.extra_header={}
             else: 
               ls4.extra_header.update(*kw_dict)

    @ property 
    def status(self):
       return self.ls4_status.get()

    def init_ls4_conf(self):
       """ initialize default values of self.ls4_conf """
     
       ls4_conf={}

       # when logging messages, the dault format is:
       ls4_conf['log_format']="# %(message)s"

       # use the controllers in synchronous mode
       ls4_conf['sync']=True

       # do not fake the calls to the controllers
       ls4_conf['fake']=False

       # the name of lead controller is the first name in self.ctrl_names list
       ls4_conf['leader']=None

       # read out the array for 30.0 sec to clear
       ls4_conf['flush_time']=30.0

       # power down controllers when LS4_Control exits
       ls4_conf['power_down']=True

       # enabled controllers
       ls4_conf['enable_list']=[]

       # default exposure time
       ls4_conf['exptime']=0.0

       # default number of exposures
       ls4_conf['init_count']=0
 
       # initialize enabled to false. Becomes true when respective LS4_CAM is instantiated
       ls4_conf['enabled'] = False    

       return ls4_conf

    def instantiate_cameras(self):
 
       # instantiate LS4_Sync , which containins parameters, lists, and 
       # synchronizing primitives and functions used to synchronize the
       # commands sent to the controllers. 

       if self.ls4_sync is not None:
          del self.ls4_sync

       self.ls4_sync = LS4_Sync(num_controllers = self.num_controllers,\
                           lead_index=self.lead_index,\
                           ls4_logger=self.ls4_logger)

       # For each enabled controller, add a new instance of  LS4_Camera  to self.ls4_list .
       # For disabaled controllers, leave the respective list member to None

       error_msg = None

       self.ls4_list=[]
       self.enabled_cam_list=[]
       for index in range(0,self.num_controllers):
         self.ls4_list += [None]
         try:
           self.ls4_list[index]=self.instantiate_cam(index)
           if self.ls4_list[index] is not None:
              self.enabled_cam_list.append(self.ls4_list[index])
         except Exception as e:
           error_msg = "Exception instantiating ls4_camera for controller %d: %s" % (index,e)
           self.ls4_logger.error(error_msg)
           self.ls4_status.update({'error':True,'comment':error_msg})
           raise RuntimeError(error_msg)

    async def initialize(self, sync_flag=None):
        """ for each instance of LS4_Camera in self.enabled_cam_list, initialize the socket
            connection to the respective controller using self.init_camera. 
            Also add the instance of LS4_Camera to the list maintained internally 
            by self.ls4_sync
        """

        self.ls4_status.update({'ready':False,'state':'initializing','comment':'initializing'})
        self.ls4_logger.info("########## %s: initializing controllers" % self.get_obsdate())

        #if controllers are synchronized, do not start timing code after initializing
        if self.sync_controllers:
           hold_timing = True

        # otherwise start the timing code after initializing
        else:
           hold_timing = False

        self.ls4_logger.debug("executing init_camera for each camera")
        await asyncio.gather(*(self.init_camera(ls4_cam,hold_timing=hold_timing,sync_flag=sync_flag) \
                              for ls4_cam in self.enabled_cam_list))
        self.ls4_logger.debug("done executing init_camera for each camera")

        self.ls4_logger.debug("setting lead for controller index %d" % self.lead_index)
        self.ls4_list[self.lead_index].set_lead(True)
        self.ls4_logger.debug("done setting lead for controller index %d" % self.lead_index)

        self.ls4_logger.debug("adding controllers to ls4_sync")

        sync_index=0
        for ls4_cam in self.enabled_cam_list:
              if ls4_cam.ls4_conf['name'] != self.leader_name:
                self.ls4_sync.add_controller(ls4_cam.ls4_controller,sync_index=sync_index)
                sync_index += 1
              else:
                self.ls4_sync.add_controller(ls4_cam.ls4_controller,sync_index=None)


        self.ls4_logger.debug("done adding %d controllers to ls4_sync" % sync_index)
        self.ls4_status.update({'ready':True,'state':'initialized','error':False,'comment':'initialized'})

    def get_obsdate(self,tm=None):
        if tm is None:
           tm=time.gmtime()
        dt = "%04d-%02d-%02dT%02d:%02d:%05.2f" % \
              (tm.tm_year,tm.tm_mon,tm.tm_mday, tm.tm_hour,tm.tm_min,tm.tm_sec)
        return dt


    async def start(self,sync_flag=None):

        """ start the controller timing code. Normally this powers up each controller and
            puts them into auto-clear loops. The
        """

        self.ls4_status.update({'state':'starting','comment':'starting'})
        self.ls4_logger.info("########## %s: starting controllers" % self.get_obsdate())

        # When synchronizing controllers, don't start the timing code until 
        # all the controllers have been separately started 
        if self.sync_controllers:
           release_timing= False

        # otherwise they can start their timing codes asynchronously
        else:
           release_timing = True
 
        self.ls4_logger.debug("executing start_controller for %d enabled camera controllers" % \
                len(self.enabled_cam_list))
        await asyncio.gather(*(self.start_controller(ls4_cam,release_timing=release_timing) \
                            for ls4_cam in self.enabled_cam_list))
        self.ls4_logger.debug("done executing start_controller for %d controllers" % \
                len(self.enabled_cam_list))
  

        # this is where the timing code is started on the synchronized controllers
        if self.sync_controllers:
           self.ls4_logger.info("########## %s: syncing controllers" % self.get_obsdate())
           await self.sync()

        self.ls4_status.update({'state':'started','comment':'started'})


    async def stop(self, stop_timing=True, power_down=True, sync_flag=None):

        """ stop the controller timing code. This also powers down each controller.
        """

        self.ls4_status.update({'state':'stopping','comment':'stopping'})
        self.ls4_logger.info("########## %s: stopping controllers" % self.get_obsdate())
        await asyncio.gather(*(self.stop_controller(ls4=ls4_cam,sync_flag=sync_flag) \
                            for ls4_cam in self.enabled_cam_list))
  
        self.ls4_status.update=({'state':'stopped','comment':'stopped'})

    async def sync(self):
        self.ls4_status.update({'state':'syncing','comment':'syncing'})
        self.ls4_logger.info("########## %s:  syncing controllers" % self.get_obsdate())
        await asyncio.gather(*(self.sync_timing(ls4_cam) for ls4_cam in self.enabled_cam_list))
        await self.ls4_sync.set_sync(True)

        self.ls4_logger.info("########## %s: testing semaphore synchronization" % self.get_obsdate())
        await self.ls4_sync.test_sync()
        #ls4_logger.info("done testing semaphore synchronization")
        self.ls4_status.update({'state':'synced','comment':'synced'})

    async def unsync(self):
        self.ls4_status.update({'state':'unsyncing','comment':'unsyncing'})
        self.ls4_logger.info("########## %s: unsyncing controllers" % self.get_obsdate())
        await self.ls4_sync.set_sync(False)
        self.ls4_status.update({'state':'unsynced','comment':'unsynced'})

    async def flush(self,flush_time=None):
        """ continuously read out camera for fixed period of time """

        dt = self.flush_time
        if flush_time is not None:
           dt = flush_time
        self.ls4_status.update({'state':'flushing','comment':'flushing for %7.3f s' % dt})
        await self.start_flush()
        await asyncio.sleep(dt)
        await self.stop_flush()
        self.ls4_status.update({'state':'flushed','comment':'flushed'})

    async def start_flush(self, sync_flag=None):
        """ start continuously .expose_out camera """
        self.ls4_logger.info("########## %s: start auto-flushing" % self.get_obsdate())
        await asyncio.gather(*(self.start_autoflush(ls4=ls4_cam,sync_flag=sync_flag)\
                        for ls4_cam in self.enabled_cam_list))

    async def stop_flush(self,sync_flag=None):
        """ stop continuously reading out camera """
        self.ls4_logger.info("########## %s: stop auto-flushing" % self.get_obsdate())
        await asyncio.gather(*(self.stop_autoflush(ls4=ls4_cam,sync_flag=sync_flag)\
               for ls4_cam in self.enabled_cam_list))

    async def expose(self,exp_number=None,exptime=None, image_prefix=None,exp_mode=None,
                     save=True, enable_shutter=True, sync_flag=None):

        """ expose for specifed or pre-configured exposure time and read out to a controller buffer.
            The time when the data are fetched depends on the value for wait.

            Output images are named "[image_prefix][ctrl_name]_[exp_number].fits"
            enable_shutter = True/False: open/don't open the shutter during the epxposure
            save = True/False to save images to disk

            exposure exp_mode values :
              exp_mode_single : acquire and fetch the same image in sequence
              exp_mode_first  : acquire a new image but do not fetch
              exp_mode_next   : fetch previous image while acquiring the next
              exp_mode_last   : fetch previous image, acquire and fetch a new one
            
        """

  
        assert exp_mode in ls4_exp_modes, "unexpected exp_mode: %s" % str(exp_mode)

        self.ls4_status.update({'state':'exposing',\
                             'comment':'exposing image %d exp_mode %s' % (self.image_count,exp_mode)})

        error_msg = None

        if exptime is None:
           exptime = self.ls4_conf['exptime']
        
        if image_prefix is None:
           image_prefix = self.ls4_conf['image_prefix']

        if exp_number is not None:
           assert isinstance(exp_number,int), "exp_number must be an integer"
           image_prefix = image_prefix + "_" + "%03d"%exp_number

        self.ls4_logger.info(\
           "########## %s: acquiring exposure %s (exp_mode: %s, expt: %7.3f shutter: %s save: %s " %\
           (self.get_obsdate(),image_prefix,exp_mode,exptime,enable_shutter,save))

        # make sure controllers are still synchronized before each exposure
        if self.sync_controllers:
           try:
             await self.sync()
           except Exception as e:
             error_msg = "Exception syncing controllers: %s" % e

        if error_msg is None:
          try:
             await asyncio.gather(*(self.expose_controller(exptime=exptime,ls4=ls4_cam,\
                       image_prefix = image_prefix,exp_mode=exp_mode, \
                       save=save,enable_shutter=enable_shutter,sync_flag=sync_flag) \
                       for ls4_cam in self.enabled_cam_list))

          except Exception as e:
             error_msg = \
                "Exception acquiring exposure %s (exp_mode: %s, expt: %7.3f shutter: %s save: %s): %s" %\
                (image_prefix,exp_mode,exptime,enable_shutter,save,e)


        # if exp_mode is 'last', then wait for the last exposure to be readout by the controller, and
        # fetch it here.
        #if exp_mode == exp_mode_last and error_msg is None:
        if 0:

            acquire = False
            fetch = True 
            wait = True
            try:
              await asyncio.gather(*(self.expose_controller(exptime=exptime,ls4=ls4_cam,\
                         image_prefix = image_prefix,exp_mode=exp_mode, \
                         save=save,enable_shutter=enable_shutter,sync_flag=sync_flag) \
                         #for index in range(0,self.num_controllers)))
                         for ls4_cam in self.enabled_cam_list))

            except Exception as e:
              error_msg = \
                "Exception fetching last exposure %s (exp_mode: %s, expt: %7.3f shutter: %s save: %s): %s" %\
                (image_prefix,exp_mode,exptime,enable_shutter,save,e)

        if error_msg is not None:
           self.ls4_status.update({'ready':False, 'state':'error','comment':error_msg})
           raise RuntimeError(error_msg)

        self.ls4_status.update({'state':'idle','comment':'done exposing image %d' % self.image_count})
        self.image_count += 1

    async def expose_controller(self,exptime=None,ls4 = None, image_prefix = None, \
              exp_mode = None, save=True, enable_shutter=None, sync_flag=None):


        """ For a given instance of LS4_Camera specified by ls4,
            expose for specifed or pre-configured exposure time and read out to a controller buffer.

            Output images are named "[image_prefix]_[ctrl_name].fits"

            enable_shutter = True/False: open/don't open the shutter during the epxposure

            There are 4 modes correspondind to different vaules for acquire/fetch/wait 

              exp_mode_first:
              True/False/True:  exposure and readout the image to controller memory, 
                                but don't fetch the data from controller.

              exp_mode_last:
              False/True/True:  fetch the last acquired image from the controller,
                                but don't expose and readout a new image

              exp_mode_single:
              True/True/True :  expose a new image, read it out to controller memory,
                                and then fetch the data

              exp_mode_next:
              True/True/False:  simultaneouslty fetch the previously acquired image, while
                                exposing a new image and reading it out to controller memory
 
            Modes where acquire and fetch are both False are not allowed                                   

            Note:  the controllers have three image buffers. As long as the time to fetch
            and optionally save an image is less than the time to readout each new image,
            then the fetching and acquiring can proceed simultaneously.
        """

        assert ls4 is not None, "instance of LS4_Camera is None"
        assert enable_shutter is not None, "enable_shutter is not specified"
        assert image_prefix is not None, "image_prefix is not specified"
        assert exp_mode in ls4_exp_modes, "unexpected exp_mode: %s" % str(exp_mode)

        ls4_conf= ls4.ls4_conf
        ctrl_name = ls4.name
        error_msg = None
        acquire = ls4_exp_modes[exp_mode]['acquire']
        fetch = ls4_exp_modes[exp_mode]['fetch']
        wait = ls4_exp_modes[exp_mode]['wait']


        if error_msg is None:
          if exptime is None:
             assert 'exptime' in ls4_conf.keys(), "exptime undefined"
             exptime = ls4_conf['exptime']
          else:
             ls4_conf['exptime']=exptime

          expt = exptime

          output_image = image_prefix + "_" + ctrl_name +  ".fits"

        if acquire and error_msg is None:
          try:
            assert await ls4.check_voltages(), "voltages out of range"
          except Exception as e:
            error_msg = e

        # acquire new image and fetch previous image at the same time
        if exp_mode == exp_mode_next:
          self.ls4_logger.debug(\
              "acquiring new image (expt time %7.3f s) while fetching previous exposure  %s" %\
                    (expt,output_image))

          # With exp_mode = exp_mode_next, two parallel are spawned to run lsq.acquire(). 
          # The actions taken by each thread depend on the values for arguments
          # acquire and fetch:
          #
          # In the first thread, acquire,fetch = True, False. This tells lsq.acquire()
          # to take a new exposure and read the data out to controller memory 
          # but not to fetch the new data from the controller to host memory.
          #
          # In the second thread,  acquire,fetch = False, True. This tells 
          # ls4.acquire() to fetch data acquired in any previous call to lsq.acquire()
          # and not to take a new exposure.
          #
          # With argument required_state = ls4.expose_state, the second thread  waits for the 
          # first thread to begin the exposure before starting to fetch 
          # to previous image data from the controller memory
          #
          # With required_state = ls4.readout_state, the second thread waits for the first thread
          # to begin reading out the new image to controller memory before starting to 
          # fetch the previous  image data
          #
          # With required_state = None, the second thread immediately fetches without waiting
          #
          #
          # 
          if exptime > 10.0:
             required_state = ls4.expose_state
             max_wait_time  = 3.0
          else:
             required_state = ls4.readout_state
             max_wait_time = expt + 3.0

          #DEBUG
          if 1:
          #try:
            await asyncio.gather(ls4.acquire(exptime=expt,output_image="None",\
                                   acquire=True,fetch=False,save=False,sync_flag=sync_flag,\
                                   enable_shutter=enable_shutter,required_state=None),\
                                 ls4.acquire(exptime=expt,output_image=output_image,\
                                   acquire=False, fetch=True,save=save,sync_flag=sync_flag,\
                                   enable_shutter=enable_shutter, required_state=required_state, \
                                   max_wait_time=max_wait_time)\
                                )
          else:
          #except Exception as e:
            error_msg = "exception acquiring while saving previous exposure: %s" % e

        # acquire and/or fetch but not at the same time (i.e.sequentially)
        elif error_msg is None:
          if acquire:
            ls4.debug("acquiring new exposure [%s] and reading out to controller" % output_image)
            try: 
               await ls4.acquire(exptime=expt,output_image="None",acquire=True,\
                      fetch=False,save=False,enable_shutter=enable_shutter, sync_flag=sync_flag,
                      required_state=None, max_wait_time=0)
            except Exception as e:
               error_msg = "exception acquiring image [%s] : %s" % (output_image,e)

          if fetch and error_msg is None :
            if save:
              ls4.debug("fetching and saving exposure [%s]" % output_image)
            else:
              ls4.debug("fetching exposure [%s] but not saving" % output_image)

            try: 
               await ls4.acquire(exptime=expt,output_image=output_image,acquire=False,\
                      fetch=True,save=save, sync_flag=sync_flag, required_state = None,\
                      max_wait_time=0)
            except Exception as e:
               error_msg = "exception saving exposure [%s]: %s" %\
                             (output_image,e)

        assert error_msg is None, error_msg


    def instantiate_cam(self,index=None):

       """ use the configuration info in self.ls4_conf[index] tor create an instance
           of  LS4_Camera and return the new instance
       """

       # for each instance of LS4_Camera to be instantiated, create a copy of ls4_conf and save
       # it in self.ls4_conf_list. Also update each copy with  a controller-specific prefix,
       # ip number, name, local netword addressing info, act file name, and map file name.
       # Instantiate LS4_camera using the copied config data to initialize. Also n 
       # using the respective copy of the configuration data as initialization arguments.

       ls4_camera = None

       name=self.ctrl_names[index]
       conf = self.ls4_conf_list[index]
       conf.update(self.ls4_conf)
       conf.update({'image_prefix':'test%d' % index})
       conf.update({'ip':self.ip_list[index]})
       conf.update({'name':name})
       conf.update({'local_addr':(self.bind_list[index],self.port_list[index])})
       conf.update({'acf_file':self.conf_path+"/"+self.acf_list[index]})
       conf.update({'map_file':self.conf_path+"/"+self.map_list[index]})
       conf.update({'enabled':False})

       if name not in self.ls4_conf['enable_list']:
          self.ls4_logger.info("Skipping instantiate of controller %s, disabled" % name)
       else:
          try:
            ls4_camera=\
              LS4_Camera(ls4_conf=conf,ls4_sync=self.ls4_sync,\
                       command_args=self.ls4_sync.command_args,\
                       param_args=self.ls4_sync.param_args)
            if ls4_camera is not None:
              conf.update({'enabled':True})
          except Exception as e:
              error_msg = "Exception instantiating LS4_Camera for index %d: %s" %\
                     (index,e)
              self.ls4_logger.error(error_msg)
              raise RuntimeError(error_msg)


       return ls4_camera

    async def start_autoflush(self,ls4=None, sync_flag=None):
        if ls4 is not None:
          ls4.debug("start autoflushing")
          await ls4.start_autoflush(sync_flag=sync_flag)

    async def stop_autoflush(self,ls4=None, sync_flag=None):
        if ls4 is not None:
          ls4.debug("stop autoflushing")
          await ls4.stop_autoflush(sync_flag=sync_flag)

    async def init_camera(self,ls4=None,hold_timing=False, sync_flag=None):

        """ initialize socket connection to controller but do not 
            configure or power up. If hold timing is True, do not
            start the timing code.
        """

        if ls4 is not None:
          ls4.debug("initializing with hold_timing = %s" % hold_timing )
          await ls4.init_controller(hold_timing=hold_timing, sync_flag=sync_flag)

    async def start_controller(self,ls4=None, release_timing=False, sync_flag=None):
        """ write configuration to controller and then power on.
            Check voltages are in range afterwards.
            If release_timing is False, do not start controller timing code
        """


        if ls4 is not None:

          ls4.debug("starting controller %s" % ls4.name)
          await ls4.start_controller(release_timing=release_timing,sync_flag=sync_flag)
          ls4.debug("done starting controller %s" % ls4.name)

      
          ls4.debug("checking voltages")
          in_range  = await ls4.check_voltages()
          ls4.debug("done checking voltages")
          if not in_range:
            ls4.warn("voltages out of range on first check. Checking again ...")
            await asyncio.sleep(1)
            assert await ls4.check_voltages(), \
                   "voltages out of range second try"


    async def stop_controller(self,ls4=None,power_down=True,sync_flag=None):
      """ power down the controller (unless power_down = False ), and
          disconnect client. The camera will continue to run its timing
          code, however.
      """

      if ls4 is not None:
        ls4.debug("stopping controller: power_down = %s" % power_down)
        await ls4.stop_controller(power_down=power_down,sync_flag=sync_flag)

    async def sync_timing(self,ls4=None, sync_flag=None):
      """ start timing code on the specified controller. If the
          controllers are synchronized by an external clock, they
          will execute their copies of the timing code in lock
          step with the lead controller.
      """

      if ls4 is not None:
        await ls4.release_timing(sync_flag=sync_flag)

##############

if __name__ == "__main__":

  async def test():

      ls4_conf={'ip_list':'10.0.0.241,10.0.0.242,10.0.0.243,10.0.0.244',
              'bind_list':'127.0.0.1,127.0.0.1,127.0.0.1,127.0.0.1',
      #ls4_conf={'ip_list':'192.168.1.1,192.168.2.1,192.168.3.1,192.168.4.1',
      #        'bind_list':'192.168.1.10,192.168.2.10,192.168.3.10,192.168.4.10',
              'enable_list':'ctrl1,ctrl2,ctrl3,ctrl4',
              'port_list':'4242,4242,4242,4242',
              'image_prefix': 'test',
              'ctrl_names': 'ctrl1,ctrl2,ctrl3,ctrl4',
              'leader':'ctrl1',
              'data_path':'/data/ls4',
              'conf_path': '/home/ls4/archon/ls4_control/conf',
              'acf_list': 'test_nw.acf,test_sw.acf,test_se.acf,test_ne.acf',
              'map_list':'test_nw.json,test_sw.json,test_se.json,test_ne.json',
              'log_level':'INFO',
              'prefix':'test',
              'sync': 'False',
              'fake': 'True',
              'save': 'True',
              'power_down':'True',
              'flush_time':3.0,
              'init_count':0}

      for key in ls4_conf:
         print("%s:%s" % (key,ls4_conf[key]))
         if isinstance(ls4_conf[key],str) and "," in ls4_conf[key]:
             ls4_conf[key]=ls4_conf[key].split(',')

      enable_shutter = True # open shuttter during exposure
      power_down = True # power down controller biases before exiting
      save =  True # save exposure image
      exptime = 1.0 # exposure time in sec

      sync_controllers=False
      if ls4_conf['sync'] in ['True','TRUE','true',True]:
         sync_controllers=True

      ls4_ctrl = LS4_Control(ls4_conf=ls4_conf)
      await ls4_ctrl.initialize(sync_flag=False)
      await ls4_ctrl.start(sync_flag=False)
      exp_mode = ls4_ctrl.exp_mode_single # readout and save  before next exposure
      await ls4_ctrl.expose(exptime=exptime,exp_number=1,sync_flag=sync_controllers,\
                  exp_mode = exp_mode, save=save, enable_shutter=enable_shutter)

      await ls4_ctrl.unsync()
      await ls4_ctrl.start_flush(sync_flag=False)
      await ls4_ctrl.stop(power_down=power_down,sync_flag=False)

  asyncio.run(test())

