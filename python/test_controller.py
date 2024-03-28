# test program for LS4 Camera
# This uses ls4_control Python code to implement basic control of the LS4 Camera
# execute "python test_controller.py -h" for help

import sys
import os
import asyncio
import archon
from archon import log
import logging
import time
import argparse

from archon.ls4.ls4_sync import LS4_Sync
from archon.controller.ls4_controller import LS4Controller
from archon.controller.ls4_logger import LS4_Logger   
from archon.ls4.ls4_camera import LS4_Camera

ls4_logger = LS4_Logger(name="main")
    
async def exp_sequence(exptime=None,ls4=None,ls4_conf=None,n_done=0, acquire=False, fetch=False, save=False, wait=True):

    """ Acquire a new exposure and/or fetch an exposure, with the following 4 modes
        depending on acquire/fetch/wait :

          True/False/True: exposure and readout the image to controller memory, 
                           but don't fetch the data from controller.

          False/True/True: fetch the last acquired image from the controller,
                           but don't expose and readout a new image

          True/True/True : expose a new image, read it out to controller memory,
                           and then fetch the data

          True/True/False: simultaneouslty fetch the previously acquired image, while
                           exposing a new image and reading it out to controller memory
                                
        Note:  the controllers have three image buffers. As long as the time to fetch
        and optionally save an image is less than the time to readout each new image,
        then the fetching and acquiring can proceed simultaneously.

    """


    assert ls4 is not None, "ls4 controller uninitialized"
    assert  acquire or fetch, "must acquire and/or fetch"

    if not wait:
       assert acquire and fetch, "must acquire and fetch if wait is false"

    error_msg = None

    if exptime is None:
       exptime = ls4_conf['exptime']
    else:
       ls4_conf['exptime']=exptime
    expt = exptime

    if acquire:
      try:
        assert await ls4.check_voltages(), "voltages out of range"
      except Exception as e:
        error_msg = e

    if error_msg is None:
      num_exposures = ls4_conf['num_exp']
      data_path=ls4_conf['data_path']
      image_prefix = ls4_conf['prefix']


    # If n_done = 0, then there is no previously acquired image to fetch. Force 
    # wait to True and fetch to False for this exposure.
    if n_done <= 1 and wait == False:
       wait = True
       fetch = False

    # acquire and fetch at the same time
    if acquire and fetch and (not wait) and error_msg is None:
      output_image = image_prefix + "_%03d"%(n_done-1) +  ".fits"
      ls4_logger.info("########## acquiring new image (expt time %7.3f s) while fetching exposure  %s" %\
                 (expt,output_image))

      try:
        await asyncio.gather(ls4.acquire(exptime=expt,output_image="None",\
                               acquire=True,fetch=False,save=False),
                             ls4.acquire(exptime=expt,output_image=output_image,\
                               acquire=False, fetch=True,save=save))
      except Exception as e:
         error_msg = "exception acquiring while saving previous exposure: %s" % e

    # acquire and/or fetch but not at the same time
    elif error_msg is None:
      if acquire:
        try: 
           ls4.info("acquiring new exposure [%d/%d] and reading out to controller" % \
                  (n_done,num_exposures))
           await ls4.acquire(exptime=expt,output_image="None",acquire=True,\
                            fetch=False,save=False)
        except Exception as e:
           error_msg = "exception acquiring image [%d/%d] : %s" % (n_done,num_exposures,e)

      if fetch and error_msg is None:
        output_image = image_prefix + "_%03d"%n_done +  ".fits"
        ls4.info("saving new exposure [%d/%d] to %s" % (n_done,num_exposures,output_image))
        try: 
           await ls4.acquire(exptime=expt,output_image=output_image,acquire=False,\
                  fetch=True,save=save)
        except Exception as e:
           error_msg = "exception saving exposure [%d/%d] to %s: %s" %\
                         (n_done,num_exposures,output_image,e)

    assert error_msg is None, error_msg

async def start_autoflush(ls4=None):
  if ls4 is not None:
    ls4.debug("start autoflushing")
    await ls4.start_autoflush()

async def stop_autoflush(ls4=None):
  if ls4 is not None:
    ls4.debug("stop autoflushing")
    await ls4.stop_autoflush()

async def init_controller(ls4=None,hold_timing=False):
  if ls4 is not None:
    ls4.debug("initializing" )
    await ls4.init_controller(hold_timing=hold_timing)

async def reset(ls4=None,release_timing=False):
  if ls4 is not None:
    ls4.debug("resetting")
    await ls4.reset(release_timing=release_timing)


async def start_controller(ls4=None, release_timing=False):
  if ls4 is not None:
    await ls4.start_controller(release_timing=release_timing)

    ls4.debug("checking voltages")
    in_range  = await ls4.check_voltages()
    if not in_range:
      ls4.warn("voltages out of range on first check. Checking again ...")
      await asyncio.sleep(1)
      assert await ls4.check_voltages(), \
             "voltages out of range second try"


async def sync_controller(ls4=None):
  if ls4 is not None:
    await ls4.release_timing()

async def stop_controller(ls4,power_down=True):
  if ls4 is not None:
    ls4.debug("stopping controller: power_down = %s" % power_down)
    await ls4.stop_controller(power_down)

def namelist(s):
    return s.split(",")

async def test():

  ls4_conf={}

  parser = argparse.ArgumentParser(description="LS4 camera control program")
  parser.add_argument('--ip_list', metavar='i', type=namelist, default='10.0.0.241,10.0.0.242,10.0.0.243,10.0.0.244',
                      help='list of controller IP addresses (cntrl 1 to 4)')
  parser.add_argument('--data_path', metavar='d', type=str, default='/data/ls4',
                      help='the path location for images and data')
  parser.add_argument('--conf_path', metavar='c', type=str, default='/home/ls4/archon/ls4/conf',
                      help='the path location for config files')
  parser.add_argument('--acf_list', metavar='a', type=namelist, \
                      default='test_nw.acf,test_sw.acf,test_se.acf,test_ne.acf',
                      help='the list of Archon config files (i.e. timing code)')
  parser.add_argument('--map_list', metavar='m', type=namelist, \
                      default='test_nw.json,test_sw.json,test_se.json,test_ne.json',
                      help='the list of ccd map files')
  parser.add_argument('--exptime', metavar='e', type=float, default=0.0,
                      help='the image exposure time in sec')
  parser.add_argument('--num_exp', metavar='n', type=int, default=1,
                      help='the number of exposures to take')
  parser.add_argument('--log_level', metavar='l', type=str, default='INFO',
                      help='the logging level(INFO, WARN, DEBUG, or ERROR)')
  parser.add_argument('--prefix', metavar='p', type=str, default='test',
                      help='the prefix for each image name')
  parser.add_argument('--leader', metavar='L', type=str, default='ctrl1',
                      help='the name of the lead controller')
  parser.add_argument('--sync', metavar='s', type=str, default="True",
                      help='sync controllers True or False')
  parser.add_argument('--test',  action='store_true',
                      help='test the controller')
  parser.add_argument('--save', metavar='S', type=str, default="True",
                      help='save images True or False')
  parser.add_argument('--fake', metavar='s', type=str, default="False",
                      help='fake controller True or False')
  parser.add_argument('--enable_list', metavar='E', type=namelist, default=['ctrl1'],
                      help='list of enabled controllers')
  parser.add_argument('--bind_list', metavar='b', type=namelist, default='127.0.0.1,127.0.0.1,127.0.0.1,127.0.0.1',
                      help='list of network ip address to bind controller connections ')
  parser.add_argument('--port_list', metavar='q', type=namelist, default='4242,4242,4242,42424',
                      help='list of network ports to bind controller connections ')
  parser.add_argument('--clear_time', metavar='c', type=float, default=30.0,
                      help='the time to initially clear the CCDs by continuously reading out')
  parser.add_argument('--power_down', type=str, default="True ",
                      help='power down on exir True or False')
  parser.add_argument('--exp_incr', type=float, default=0.2,
                      help='the amount to increment the exposture time every other exposure')

  ls4_conf.update(vars(parser.parse_args()))
  #ls4_logger.info("########## ls4_conf: %s" % ls4_conf)

  #if ls4_conf['log_level'] == 'DEBUG':
  #   ls4_conf['log_format']="#[%(filename)s:%(lineno)s:%(funcName)s] %(message)s"
  #else:
  #   ls4_conf['log_format']="# %(message)s"
  ls4_conf['log_format']="# %(message)s"

  #ls4_logger = LS4_Logger(name="main")


  exptime = ls4_conf['exptime']
  num_controllers = None
  ls4_list=[None,None,None,None]
  ctrl_names = ['ctrl1','ctrl2','ctrl3','ctrl4']
  ls4_conf_list=[{},{},{},{}]
  ip_list = ls4_conf['ip_list']
  port_list = ls4_conf['port_list']
  bind_list = ls4_conf['bind_list']
  conf_path = ls4_conf['conf_path']
  acf_list = ls4_conf['acf_list']
  map_list = ls4_conf['map_list']
  num_exp = ls4_conf['num_exp']
  clear_time = ls4_conf['clear_time']
  leader_name = ls4_conf['leader']
  num_controllers = len(port_list)
  exp_incr = ls4_conf['exp_incr']


  if ls4_conf['sync'] in ['True','TRUE','T','true']:
     sync_controllers = True
  else:
     sync_controllers = False

  if ls4_conf['save'] in ['True','TRUE','T','true']:
     save_images = True
  else:
     save_images = False

  if ls4_conf['fake'] in ['True','TRUE','T','true']:
     fake_controller = True
  else:
     fake_controller = False

  if ls4_conf['power_down'] in ['True','TRUE','T','true']:
     power_down = True
  else:
     power_down = False

  assert len(ip_list) == num_controllers, "number of ip address [%d] must be %d" % (len(ip_list),num_controllers)
  assert sync_controllers in [True,False],\
        "sync_controllers must be True or False"

  lead_index=None
  if sync_controllers:
    assert leader_name in ["ctrl1","ctrl2","ctrl3","ctrl4"],\
         "leader_name must be ctrl1, ctrl2, ctrl3, or ctrl4"
    assert leader_name in ls4_conf['enable_list'], "lead controller %s is not enabled" % leader_name
    lead_index = ctrl_names.index(leader_name)
  else:
    lead_index=0

  ls4_sync = LS4_Sync(num_controllers = num_controllers,lead_index=lead_index,ls4_logger=ls4_logger)

  ls4_logger.info("########## instantiating controllers: %s" % ctrl_names)

  lead_enabled = False
  for index in range(0,num_controllers):
      name=ctrl_names[index]
      conf = ls4_conf_list[index]
      conf.update(ls4_conf)
      conf.update({'prefix':'test%d' % index})
      conf.update({'ip':ip_list[index]})
      conf.update({'name':name})
      conf.update({'local_addr':(bind_list[index],port_list[index])})
      conf.update({'acf_file':conf_path+"/"+acf_list[index]})
      conf.update({'map_file':conf_path+"/"+map_list[index]})

      if name in ls4_conf['enable_list']:
         ls4_list[index]=LS4_Camera(ls4_conf=conf,ls4_sync=ls4_sync,
               command_args=ls4_sync.command_args,param_args=ls4_sync.param_args,
               fake=fake_controller)
         if name == leader_name:
            lead_enabled = True
      else:
         ls4_logger.info("########## controller %s is disabled" % name)
         ls4_list[index]=None

  if sync_controllers:
     assert lead_enabled, "leader %s was not enabled" % leader_name
     hold_timing = True
     release_timing= False
  else:
     hold_timing = False
     release_timing = True

  ls4_logger.info("########## initializing controllers, hold_timing = %s" % hold_timing)

  await asyncio.gather(*(init_controller(ls4_ctr,hold_timing=hold_timing) for ls4_ctr in ls4_list))

  ls4_list[lead_index].set_lead(True)

  sync_index=0
  for index in range(0,num_controllers):
     if ls4_list[index] is not None:
        if index != lead_index:
          ls4_sync.add_controller(ls4_list[index].ls4_controller,sync_index=sync_index)
          sync_index += 1
        else:
          ls4_sync.add_controller(ls4_list[index].ls4_controller,sync_index=None)

  ls4_logger.info("########## starting controllers")
  await asyncio.gather(*(start_controller(ls4_ctr,release_timing=release_timing) for ls4_ctr in ls4_list))

  if sync_controllers:
    ls4_logger.info("########## syncing controllers")
    await asyncio.gather(*(sync_controller(ls4_ctr) for ls4_ctr in ls4_list))
    await ls4_sync.set_sync(True)
    #ls4_logger.info("##########  testing semaphore synchronization")
    await ls4_sync.test_sync()
    #ls4_logger.info("done testing semaphore synchronization")

  if num_exp > 0:
    ls4_logger.info("##########  start auto-flushing for %7.3f sec" % clear_time)
    await asyncio.gather(*(start_autoflush(ls4_ctr) for ls4_ctr in ls4_list))
    time.sleep(clear_time)
    ls4_logger.info("########## done auto-flushing")
    await asyncio.gather(*(stop_autoflush(ls4_ctr) for ls4_ctr in ls4_list))

  fail = False
  n_done = 1
  abort = False
  while ( n_done <= num_exp and not fail and not abort):


    if (n_done == 2*int(n_done/2)) and n_done > 2:
       exptime += exp_incr
          
    if sync_controllers:
      try:
        #ls4_logger.info("########## sleeping 3 sec")
        #await asyncio.sleep(3)
        ls4_logger.info("########## exposure %d: setting sync true" % n_done)
        await ls4_sync.set_sync(True)
        ls4_logger.info("########## exposure %d: testing semaphore synchronization" % n_done)
        await ls4_sync.test_sync()
        #ls4_logger.info("exposure %d: done testing semaphore synchronization" % n_done)
      except Exception as e:
        ls4_logger.info("########## Exception syncing controllers: %s" %e)
        fail = True

    if  num_exp == 1:
      wait = True 
    else:
      wait = False

    if not fail and not wait:
      #DEBUG
      if 1:
        ls4_logger.info("########## acquiring exposure %d with exptime %7.3f" % (n_done,exptime))

        await asyncio.gather(*(exp_sequence(exptime=exptime,ls4=ls4_list[index],\
                     ls4_conf= ls4_conf_list[index],n_done=n_done,acquire=True,\
                     fetch=True,save=save_images,wait=wait) for index in range(0,num_controllers)))
         
      #except Exception as e:
      #    ls4_logger.info("########## Exception exposing and fetching as the same time: %s" % e)
      #    fail = True

      # readout last exposure here 
      if n_done == num_exp and not fail:

        try:
          ls4_logger.info("########## fetching last exposure %d " % n_done)
          await asyncio.gather(*(exp_sequence(exptime=exptime,ls4=ls4_list[index],\
                       ls4_conf= ls4_conf_list[index],n_done=n_done,acquire=False,\
                       fetch=True,save=save_images) for index in range(0,num_controllers)))

        except Exception as e:
          ls4_logger.info("########## Exception fetching last exposure %d: %s" % (n_done,e))
          fail = True

 
    if (not fail) and wait:
      try:
        exptime = exptime + int(n_done/2)*exp_incr
        ls4_logger.info("########## acquiring exposure %d with exptime %7.3f" % (n_done,exptime))

        await asyncio.gather(*(exp_sequence(exptime=exptime,ls4=ls4_list[index],\
                     ls4_conf= ls4_conf_list[index],n_done=n_done,acquire=True,\
                     fetch=False,save=False) for index in range(0,num_controllers)))
         
      except Exception as e:
          ls4_logger.info("########## Exception exposing without fetching: %s" % e)
          fail = True
 
    if (not fail) and wait:
      if sync_controllers:
        try:
          await ls4_sync.set_sync(False)
          #ls4_logger.info("########## testing semaphore synchronization")
          #await ls4_sync.test_sync()
        except Exception as e:
          ls4_logger.info("########## Exception unsetting synchronization: %s" %e)
          fail = True

    if not fail and wait:
      try:
        ls4_logger.info("########## fetching exposure %d " % n_done)
        await asyncio.gather(*(exp_sequence(exptime=exptime,ls4=ls4_list[index],\
                     ls4_conf= ls4_conf_list[index],n_done=n_done,acquire=False,\
                     fetch=True,save=save_images) for index in range(0,num_controllers)))

      except Exception as e:
        ls4_logger.info("########## Exception fetching image %d: %s" % (n_done,e))
        fail = True

    n_done += 1

    if os.path.exists("/tmp/abort_ls4"):
       abort=True
       break
         
  if sync_controllers:
    await ls4_sync.set_sync(False)

  if abort:
     ls4_logger.critical("exposure aborted")

  ls4_logger.info("########## start autoflushing")

  await asyncio.gather(*(start_autoflush(ls4_ctr) for ls4_ctr in ls4_list))

  ls4_logger.info("########## stopping controllers")
  await asyncio.gather(stop_controller(ls4_list[0],power_down),\
                       stop_controller(ls4_list[1],power_down),\
                       stop_controller(ls4_list[2],power_down),\
                       stop_controller(ls4_list[3],power_down))

  ls4_logger.info("########## exiting")

asyncio.run(test())
