############################
# -*- coding: utf-8 -*-
#
# @Author: David Rabinowitz (david.rabinowitz@yale.edu)
# @Date: 2025-06-25
# @Filename: ls4_conf.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)
#
# Python code defining LS4_Conf class 
#
# This provides code to read configuration parameters from
# the command line or from a configuration files
#
################################


import sys
import os
import asyncio
import archon
from archon import log
import logging
import time
import argparse
import platform
from archon.controller.ls4_logger import LS4_Logger

   
def namelist(s):
    return s.split(",")


class LS4_Conf():
    """ class to handle configuration parameters """

    hostname = platform.node()

    def __init__(self,logger=None,ls4_conf_file=None,init_conf=None,parse_args=False):

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

        if logger is None:
           self.logger = LS4_Logger(name="LS4_CCP")
        else:
           self.logger = logger

        if not parse_args:
          assert [init_conf,ls4_conf_file] != [None,None],\
            "must specify init_conf or ls4_conf_file when parse_args is False"

        self.conf = {}
         
        # initialize self.conf with default configuration
        self.conf.update(self.default_conf())

        # update self.conf with entries from init_conf argument
        if init_conf is not None:
          self.conf.update(init_conf)

        # update with entries from conf file
        if ls4_conf_file is not None:
          try:
            error_msg = self.read_conf_file(ls4_conf_file)
          except Exception as e:
            error_msg = "Exception loading conf file %s: %s" %\
                  (ls4_conf_file,e)

        # update with command-line arguments
        if parse_args:
           self.conf.update(self.parse_command_line())

        # check that critical parameters are specified by self.conf

        critical_params = ['ip_list','bind_list','conf_path','data_path',\
                           'acf_list','map_list','clear_time','image_prefix',\
                           'leader','port_list','sync','fake','reset','initial_reboot',\
                           'power_down', 'name_list','enable_list','init_count',\
                           'server_name', 'server_port', 'status_port']

        for param in critical_params:
            assert param in self.conf,"critical parameter %s missing from conf" % param

        # make sure lists have equal lengths
        critical_lists = ['ip_list','bind_list','acf_list','map_list',\
                           'port_list','name_list']
        n = len(self.conf['name_list'])

        for list_name in critical_lists:
          assert len(self.conf[list_name]) == n,\
            "len of list %s is not %d" % (list_name,n)

        if 'log_format' in self.conf and self.conf['log_format'] is not None:
           self.logger.debug("setting log format to %s" % self.conf['log_format'])
           self.logger.set_format(self.conf['log_format'])

    def default_conf(self):
       """ initialize default values of self.conf """
     
       conf={}

       # when logging messages, the dault format is:
       conf['log_format']="# %(message)s"

       # use the controllers in synchronous mode
       conf['sync']=True

       # do not fake the calls to the controllers
       conf['fake']=False

       # the name of lead controller is the first name in self.name_list list
       conf['leader']=None

       # read out the array for 30.0 sec to clear
       conf['clear_time']=30.0

       # power down controllers when LS4_Control exits
       conf['power_down']=True

       # enabled controllers
       conf['enable_list']=[]

       # default exposure time
       conf['exptime']=0.0

       # default number of exposures
       conf['init_count']=0
 
       # initialize enabled to false. Becomes true when respective LS4_CAM is instantiated
       conf['enabled'] = False    

       # default is to read CCD out through both amps
       conf['amp_direction']="both"

       return conf

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

    def parse_command_line(self):
       """ parse the command line to initialize configuration parameters """

       conf={}

       parser = argparse.ArgumentParser(description="LS4 camera control program")
       parser.add_argument('--ip_list', metavar='i', type=namelist,\
                               default='192.168.1.1,192.168.2.1,192.168.3.1,192.168.4.1',
                           help='list of controller IP addresses (cntrl 1 to 4)')
       parser.add_argument('--name_list', metavar='N', type=namelist, default=['ctrl1','ctrl2','ctrl3','ctrl4'],
                           help='list of controller names')
       parser.add_argument('--data_path', metavar='d', type=str, default='/home/ls4/data/test',
                           help='the path location for images and data')
       parser.add_argument('--conf_path', metavar='c', type=str, default='/home/ls4/archon/ls4_control/conf',
                           help='the path location for config files')
       parser.add_argument('--acf_list', metavar='a', type=namelist, \
                           default='test_ne.acf,test_se.acf,test_nw.acf,test_sw.acf',
                           #default='test_ne_1024.acf,test_se_1024.acf,test_nw_1024.acf,test_sw_1024.acf',
                           help='the list of Archon config files (i.e. timing code)')
       parser.add_argument('--map_list', metavar='m', type=namelist, \
                           default='test_ne.json,test_se.json,test_nw.json,test_sw.json',
                           help='the list of ccd map files')
       parser.add_argument('--exptime', metavar='e', type=float, default=0.0,
                           help='the image exposure time in sec')
       parser.add_argument('--num_exp', metavar='n', type=int, default=1,
                           help='the number of exposures to take')
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
       parser.add_argument('--fake', metavar='s', type=str, default="False",
                           help='fake controller True or False')
       parser.add_argument('--enable_list', metavar='E', type=namelist, default=['ctrl1','ctrl2','ctrl3','ctrl4'],
                           help='list of enabled controllers')
       parser.add_argument('--bind_list', metavar='b', type=namelist, \
                           default='192.168.1.10,192.168.2.10,192.168.3.10,192.168.4.10',
                           help='list of network ip address to bind controller connections ')
       parser.add_argument('--port_list', metavar='q', type=namelist, default='0,0,0,0',
                           help='list of network ports to bind controller connections ')
       parser.add_argument('--clear_time', metavar='c', type=float, default=30.0,
                           help='the time to initially clear the CCDs by continuously reading out')
       parser.add_argument('--power_down', type=str, default="True ",
                           help='power down on exir True or False')
       parser.add_argument('--initial_clear', type=str, default="False",
                           help='initially clear camera on start up, True or False')
       parser.add_argument('--idle_function', type=str, default="none",
                           help='controller idle function (none,clear,or flush)')
       parser.add_argument('--exp_incr', type=float, default=0.2,
                           help='the amount to increment the exposture time every other exposure')
       parser.add_argument('--delay', type=float, default=0.0,
                           help='delay (sec) between exposure pairs')
       parser.add_argument('--shutter_mode', type=str, default="open",
                      help='choose alternate, dark, or open')
       parser.add_argument('--server_name', metavar='H', type=str, 
                           default=self.hostname,
                      help='name of the command server host')
       parser.add_argument('--server_port', metavar='P', type=int, default=5000,
                      help='port number of the command server')
       parser.add_argument('--status_port', metavar='Q', type=int, default=5001,
                      help='port number of the status server')
       parser.add_argument('--reset', metavar='R', type=str, default="False",
                      help='reset the controllers and exit')
       parser.add_argument('--initial_reboot', metavar='B', type=str,
                      default="False",
                      help='initially reboot controllers before configuring')
       parser.add_argument('--amp_direction', type=str, default="both",
                       help='choose both, left, or right')



       conf.update(vars(parser.parse_args()))

       
       return conf
