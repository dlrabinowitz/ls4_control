import sys
import asyncio
import archon
from archon import log
import logging
import time
import argparse

from archon.ls4.ls4_sync import LS4_Sync
from archon.ls4.ls4_controller import LS4Controller
from archon.ls4.ls4_camera import LS4_Camera

    
async def exp_sequence(ls4=None,ls4_conf=None):
  if ls4 is not None:
    #print ("erasing")
    #await ls4.ls4_controller.erase()
    #print ("purging")
    #await ls4.ls4_controller.purge(fast=True)
    #print ("cleaning")
    #await ls4.ls4_controller.cleanup(n_cycles=1)

    error_msg = None
    n_done = 1
    num_exposures = ls4_conf['num_exp']
    data_path=ls4_conf['data_path']
    image_prefix = ls4_conf['prefix']
    exptime = ls4_conf['exptime']

    while n_done <=  num_exposures and error_msg is None:

      #expt = (float(n_done)/float(num_exposures))*exptime
      expt = exptime
      #output_image = data_path + "/" + image_prefix + "_%03d"%n_done +  ".fits"
      output_image = image_prefix + "_%03d"%n_done +  ".fits"
      ls4.info("acquiring exposure %d/%d:  %s" % (n_done,num_exposures,output_image))
      #DEBUG
      try: 
         await ls4.acquire(exptime=expt,output_image=output_image)
         time.sleep(1)
         n_done += 1
      except Exception as e:
         error_msg = "exception acquiring image %d/%d : %s" % (n_done,num_exposures,e)

    if error_msg is not None:
      ls4.error(error_msg)
      raise RuntimeError(error_msg)


async def init_controller(ls4,hold_timing=False):
  if ls4 is not None:
    print ("%s: initializing" % ls4.name)
    await ls4.init_controller(hold_timing=hold_timing)


async def start_controller(ls4, release_timing=False):
  if ls4 is not None:
    print ("%s: starting" % ls4.name)
    await ls4.start_controller(release_timing=release_timing)
    #print ("erasing")
    #await ls4.ls4_controller.erase()
    #print ("purging")
    #await ls4.ls4_controller.purge(fast=True)
    #print ("cleaning")
    #await ls4.ls4_controller.cleanup(n_cycles=1)

async def sync_controller(ls4):
  if ls4 is not None:
    print ("%s: syncing" % ls4.name)
    await ls4.release_timing()

async def stop_controller(ls4):
  if ls4 is not None:
    print ("%s: stopping" % ls4.name)
    await ls4.stop_controller()

def namelist(s):
    return s.split(",")

async def test():

  sync_controllers=True
  #sync_controllers=False
  leader_name = "ctrl1"

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
  parser.add_argument('--test',  action='store_true',
                      help='test the controller')
  parser.add_argument('--enable_list', metavar='l', type=namelist, default=['ctrl1'],
                      help='list of enabled controllers')
  parser.add_argument('--bind_list', metavar='b', type=namelist, default='127.0.0.1,127.0.0.1,127.0.0.1,127.0.0.1',
                      help='list of network ip address to bind controller connections ')
  parser.add_argument('--port_list', metavar='q', type=namelist, default='4242,4242,4242,42424',
                      help='list of network ports to bind controller connections ')

  ls4_conf.update(vars(parser.parse_args()))


  num_controllers = 4
  ls4_list=[None,None,None,None]
  ctrl_names = ['ctrl1','ctrl2','ctrl3','ctrl4']
  ls4_conf_list=[{},{},{},{}]
  ip_list = ls4_conf['ip_list']
  port_list = ls4_conf['port_list']
  bind_list = ls4_conf['bind_list']
  conf_path = ls4_conf['conf_path']
  acf_list = ls4_conf['acf_list']
  map_list = ls4_conf['map_list']

  assert len(ip_list) == num_controllers, "number of ip address [%d] must be %d" % (len(ip_list),num_controllers)

  ls4_sync = LS4_Sync()

  lead_enabled = False
  lead_index = None
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
         ls4_list[index]=LS4_Camera(ls4_conf=conf)
         if name == leader_name:
            lead_enabled = True
            lead_index = index
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
  await asyncio.gather(init_controller(ls4_list[0],hold_timing=hold_timing),\
                       init_controller(ls4_list[1],hold_timing=hold_timing),\
                       init_controller(ls4_list[2],hold_timing=hold_timing),\
                       init_controller(ls4_list[3],hold_timing=hold_timing))

  for index in range(0,num_controllers):
     if ls4_list[index] is not None:
       if ls4_list[index].name == leader_name:
          ls4_sync.add_controller(ls4_list[index].ls4_controller,lead_flag=True)
       else:
          ls4_sync.add_controller(ls4_list[index].ls4_controller,lead_flag=False)

  print("starting controllers")
  await asyncio.gather(start_controller(ls4_list[0],release_timing=release_timing),\
                       start_controller(ls4_list[1],release_timing=release_timing),\
                       start_controller(ls4_list[2],release_timing=release_timing),\
                       start_controller(ls4_list[3],release_timing=release_timing))

  if sync_controllers:
    print("syncing controllers")
    await asyncio.gather(sync_controller(ls4_list[0]),\
                       sync_controller(ls4_list[1]),\
                       sync_controller(ls4_list[2]),\
                       sync_controller(ls4_list[3]))
 
    ls4_sync.set_sync(True)
 
  print("acquiring images")
  await asyncio.gather(exp_sequence(ls4_list[0],ls4_conf_list[0]),\
                       exp_sequence(ls4_list[1],ls4_conf_list[1]),\
                       exp_sequence(ls4_list[2],ls4_conf_list[2]),\
                       exp_sequence(ls4_list[3],ls4_conf_list[3]))

  if sync_controllers:
    ls4_sync.set_sync(False)

  print("stopping controllers")
  await asyncio.gather(stop_controller(ls4_list[0]),stop_controller(ls4_list[1]),stop_controller(ls4_list[2]),stop_controller(ls4_list[3]))

  print("exiting")

asyncio.run(test())
