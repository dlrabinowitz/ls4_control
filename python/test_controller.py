import sys
import asyncio
import archon
from archon import log
import logging
import time
import argparse

from archon.ls4.ls4_sync import LS4_Sync
from archon.controller.ls4_controller import LS4Controller
from archon.ls4.ls4_camera import LS4_Camera

    
async def exp_sequence(exptime=None,ls4=None,ls4_conf=None,n_done=0, acquire=False, fetch=False, save=False):
  error_msg = None

  if ls4 is not None:
    #print ("erasing")
    #await ls4.ls4_controller.erase()
    #print ("purging")
    #await ls4.ls4_controller.purge(fast=True)
    #print ("cleaning")
    #await ls4.ls4_controller.cleanup(n_cycles=1)

    try:
      assert await ls4.check_voltages(), "voltages out of range"
    except Exception as e:
      error_msg = e

    if error_msg is None:
      num_exposures = ls4_conf['num_exp']
      data_path=ls4_conf['data_path']
      image_prefix = ls4_conf['prefix']
      if exptime is None:
         exptime = ls4_conf['exptime']
      else:
         ls4_conf['exptime']=exptime
      expt = exptime

    if acquire and error_msg is None:
      # DEBUG
      try: 
         ls4.info("acquiring image %d and reading out to controller" % n_done)
         await ls4.acquire(exptime=expt,output_image="None",acquire=True,fetch=False,save=False)
         time.sleep(1)
      except Exception as e:
         error_msg = "exception acquiring  throw-away image : %s" % e

    if error_msg is None and fetch:

      expt = exptime
      output_image = image_prefix + "_%03d"%n_done +  ".fits"
      ls4.info("fetching exposure %d/%d:  %s" % (n_done,num_exposures,output_image))
      try: 
         await ls4.acquire(exptime=expt,output_image=output_image,acquire=False,fetch=True,save=save)
         #time.sleep(1)
         #n_done += 1
      except Exception as e:
         error_msg = "exception fetching and saving image %d/%d : %s" % (n_done,num_exposures,e)

    assert error_msg is None, error_msg

async def start_autoflush(ls4=None):
  if ls4 is not None:
    #print ("%s: start autoflushing" % ls4.name)
    await ls4.start_autoflush()

async def stop_autoflush(ls4=None):
  if ls4 is not None:
    #print ("%s: stop autoflushing" % ls4.name)
    await ls4.stop_autoflush()

async def init_controller(ls4=None,hold_timing=False):
  if ls4 is not None:
    #print ("%s: initializing" % ls4.name)
    await ls4.init_controller(hold_timing=hold_timing)

async def reset(ls4=None,release_timing=False):
  if ls4 is not None:
    #print ("%s: resetting" % ls4.name)
    await ls4.reset(release_timing=release_timing)


async def start_controller(ls4=None, release_timing=False):
  if ls4 is not None:
    #print ("%s: starting" % ls4.name)
    await ls4.start_controller(release_timing=release_timing)
    #print ("Erasing")
    #await ls4.ls4_controller.erase()
    #print ("Purging")
    #await ls4.ls4_controller.purge(fast=True)
    #print ("Cleaning")
    #await ls4.ls4_controller.cleanup(n_cycles=1)
    #print ("done cleaning")

    ls4.info("checking voltages")
    in_range  =await ls4.check_voltages()
    if not in_range:
      ls4.warn("voltages out of range on first check. Checking again ...")
      await asyncio.sleep(1)
      assert await ls4.check_voltages(), "voltages out of range second try"


async def sync_controller(ls4=None):
  if ls4 is not None:
    #print ("%s: syncing" % ls4.name)
    await ls4.release_timing()
    #print ("%s: done syncing" % ls4.name)

async def stop_controller(ls4,power_down=True):
  if ls4 is not None:
    #print ("%s: stopping" % ls4.name)
    await ls4.stop_controller(power_down)
    #print ("%s: done stopping" % ls4.name)

def namelist(s):
    return s.split(",")

async def test():

  ls4_conf={}

  ls4_conf['log_format']="[####%(filename)s:%(lineno)s:%(funcName)s### ] %(message)s"

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
  parser.add_argument('--enable_list', metavar='E', type=namelist, default=['ctrl1'],
                      help='list of enabled controllers')
  parser.add_argument('--bind_list', metavar='b', type=namelist, default='127.0.0.1,127.0.0.1,127.0.0.1,127.0.0.1',
                      help='list of network ip address to bind controller connections ')
  parser.add_argument('--port_list', metavar='q', type=namelist, default='4242,4242,4242,42424',
                      help='list of network ports to bind controller connections ')
  parser.add_argument('--clear_time', metavar='c', type=float, default=30.0,
                      help='the time to initially clear the CCDs by continuously reading out')

  ls4_conf.update(vars(parser.parse_args()))
  #print("ls4_conf: %s" % ls4_conf)


  # power down at end of sequence if True (or if exception occurs)
  power_down=True 

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

  if ls4_conf['sync'] in ['True','TRUE','T','true']:
     sync_controllers = True
  else:
     sync_controllers = False

  if ls4_conf['save'] in ['True','TRUE','T','true']:
     save_images = True
  else:
     save_images = False

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

  ls4_sync = LS4_Sync(num_controllers = num_controllers,lead_index=lead_index)

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
         print("instantiating controller %s" % name)
         ls4_list[index]=LS4_Camera(ls4_conf=conf,param_args=ls4_sync.param_args,
               command_args=ls4_sync.command_args)
         if name == leader_name:
            lead_enabled = True
      else:
         print("controller %s is disabled" % name)
         ls4_list[index]=None

  if sync_controllers:
     assert lead_enabled, "leader %s was not enabled" % leader_name
     hold_timing = True
     release_timing= False
  else:
     hold_timing = False
     release_timing = True

  print("initialzing controllers")
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

  print("starting controllers")
  await asyncio.gather(*(start_controller(ls4_ctr,release_timing=release_timing) for ls4_ctr in ls4_list))

  if sync_controllers:
    print("syncing controllers")
    await asyncio.gather(*(sync_controller(ls4_ctr) for ls4_ctr in ls4_list))
    await ls4_sync.set_sync(True)
    print("testing semaphore synchronization")
    await ls4_sync.test_sync()
    print("done testing semaphore synchronization")

  if num_exp > 0:
    print("################start auto-flushing for %7.3f sec", clear_time)
    await asyncio.gather(*(start_autoflush(ls4_ctr) for ls4_ctr in ls4_list))
    time.sleep(clear_time)
    print("################stop auto-flushing")
    await asyncio.gather(*(stop_autoflush(ls4_ctr) for ls4_ctr in ls4_list))

  fail = False
  n_done = 1
  while ( n_done <= num_exp and not fail):
          
    if sync_controllers:
      try:
        print("sleeping 3 sec")
        await asyncio.sleep(3)
        print("exposure %d: setting sync true" % n_done)
        await ls4_sync.set_sync(True)
        print("exposure %d: testing semaphore synchronization" % n_done)
        await ls4_sync.test_sync()
        print("exposure %d: done testing semaphore synchronization" % n_done)
      except Exception as e:
        print("exception syncing controllers: %s" %e)
        fail = True

    if not fail:
      try:
        exptime = exptime + int(n_done/2)*0.05 
        print("###############acquiring exposure %d with exptime %7.3f" % (n_done,exptime))

        await asyncio.gather(*(exp_sequence(exptime=exptime,ls4=ls4_list[index],\
                     ls4_conf= ls4_conf_list[index],n_done=n_done,acquire=True,\
                     fetch=False,save=False) for index in range(0,num_controllers)))
         
      except Exception as e:
          print("exception exposing without fetching: %s" % e)
          fail = True
 
    if not fail:
      if sync_controllers:
        try:
          await ls4_sync.set_sync(False)
          #print("testing semaphore synchronization")
          #await ls4_sync.test_sync()
        except Exception as e:
          print("exception unsetting synchronization: %s" %e)
          fail = True

    if not fail:
      try:
        print("################fetching exposure %d " % n_done)
        await asyncio.gather(*(exp_sequence(exptime=exptime,ls4=ls4_list[index],\
                     ls4_conf= ls4_conf_list[index],n_done=n_done,acquire=False,\
                     fetch=True,save=save_images) for index in range(0,num_controllers)))
        """
        await asyncio.gather(\
                exp_sequence(ls4=ls4_list[0],ls4_conf= ls4_conf_list[0],\
                            n_done=n_done,acquire=False,fetch=True,save=save_images),\
                exp_sequence(ls4=ls4_list[1],ls4_conf=ls4_conf_list[1],\
                            n_done=n_done,acquire=False,fetch=True,save=save_images),\
                exp_sequence(ls4=ls4_list[2],ls4_conf=ls4_conf_list[2],\
                            n_done=n_done,acquire=False,fetch=True,save=save_images),\
                exp_sequence(ls4=ls4_list[3],ls4_conf=ls4_conf_list[3],\
                            n_done=n_done,acquire=False,fetch=True,save=save_images))
        """

      except Exception as e:
        print("Exception fetching image %d: %s" % (n_done,e))
        fail = True


    n_done += 1
         
  if sync_controllers:
    await ls4_sync.set_sync(False)


  print("######################stopping controllers")
  await asyncio.gather(stop_controller(ls4_list[0],power_down),\
                       stop_controller(ls4_list[1],power_down),\
                       stop_controller(ls4_list[2],power_down),\
                       stop_controller(ls4_list[3],power_down))

  print("exiting")

asyncio.run(test())
