# class to simulate controller operations

# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2021-01-19
# @Filename: archon.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)
#
# @Author: David Rabinowitz (david.rabinowitz@yale.edu)
# @Date: 2024-01-16
# @Filename: ls4_fake_controller.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)
#
#
# This is an extension of the controller.py in sdss-archon
# distribution (on github)

from __future__ import annotations

import asyncio
import configparser
import io
import os
import re
import warnings
import time
import sys
from collections.abc import AsyncIterator

from typing import Any, Callable, Iterable, Literal, Optional, cast, overload

import numpy
import threading
from archon.controller.ls4_device import LS4_Device
from archon.controller.ls4_sync_io import LS4_SyncIO

from archon import config as lib_config
from archon import log
from archon.controller.command import ArchonCommand, ArchonCommandStatus
from archon.controller.maskbits import ArchonPower, ControllerStatus, ModType
from archon.exceptions import (
    ArchonControllerError,
    ArchonControllerWarning,
    ArchonUserWarning,
)

from archon.controller.ls4_params import\
              MAX_COMMAND_ID, MAX_CONFIG_LINES, FOLLOWER_TIMEOUT_MSEC, \
              P100_SUPPLY_VOLTAGE, N100_SUPPLY_VOLTAGE, \
              STATUS_LOCK_TIMEOUT, LS4_BLOCK_SIZE, \
              VSUB_ENABLE_KEYWORD, VSUB_MODULE, VSUB_ENABLE_VAL, \
              VSUB_DISABLE_VAL, VSUB_APPLY_COMMAND, MAX_FETCH_TIME, \
              STATUS_START_BIT,REBOOT_TIME, POST_ERASE_DELAY,\
              FAKE_LINECOUNT, FAKE_PIXELCOUNT, FAKE_AMPS_PER_CCD,\
              FAKE_CCDS_PER_QUAD, FAKE_BYTES_PER_PIXEL


#DEBUG
READOUT_TIME = 5 # for fake-controller testing
FETCH_TIME = 5 # for fake-controller testing

__all__ = ["LS4Controller","TimePeriod","Fake_Control"]

class LS4_Fake_Control():

    """ to keep to generate and keep track of fake data and parameters """


    def __init__(self, ls4_logger=None, notifier=None):

        self.count = 0
        self.power_status = None
        self.buffers = [None,None,None]
        self.conf={}
        self.num_buffers = 3
        self.buf_indices = list(range(1,self.num_buffers+1))
 

        if ls4_logger is None:
           self.ls4_logger = LS4_Logger(name=name)
        else:
           self.ls4_logger=ls4_logger

        if notifier is None:
           self.notifier = self.ls4_logger.debug
        else:
           self.notifier = notifier

        self.info = self.ls4_logger.info
        self.debug = self.ls4_logger.debug
        self.warn= self.ls4_logger.warn
        self.error= self.ls4_logger.error
        self.critical= self.ls4_logger.critical

        # for synchronizing acess to frame_info
        self.debug("instantiating status lock")
        self.status_lock = threading.Lock()

        # house-keeping variable to simulate readout
        self.t_read_start = 0
        self.total_lines_read = 0
         
        # dictionary required by LS4Controller class
        self.frame_info = {}


        # update additional fake-controller parameters.
        #

        assert FAKE_BYTES_PER_PIXEL in [1,2,4], "unacceptable FAKE_BYTES_PER_PIXEL: %d" % FAKE_BYTES_PER_PIXEL
        self.image_bytes=FAKE_LINECOUNT*FAKE_PIXELCOUNT*FAKE_AMPS_PER_CCD*FAKE_CCDS_PER_QUAD*FAKE_BYTES_PER_PIXEL
        if FAKE_BYTES_PER_PIXEL == 1:
           data_type = numpy.uint8
        elif FAKE_BYTES_PER_PIXEL == 2:
           data_type = numpy.uint16
        else:
           data_type = numpy.uint32
        try:
          self.update(bytes_per_pixel=FAKE_BYTES_PER_PIXEL,\
                   data_type=data_type,
                   amps_per_ccd=FAKE_AMPS_PER_CCD,\
                   ccds_per_quad=FAKE_CCDS_PER_QUAD,\
                   linecount=FAKE_LINECOUNT,\
                   pixelcount=FAKE_PIXELCOUNT)
        except Exception as e:
          error_msg = "exception updating: %s" %e
          self.error(error_msg)

        self.system_keys=['BACKPLANE_ID=0024498A715E301C', \
                    'BACKPLANE_REV=2',\
                    'BACKPLANE_TYPE=1',\
                    'BACKPLANE_VERSION=1.0.408',\
                    'MOD1_ID=0000000000000000',  \
                    'MOD1_REV=0',\
                    'MOD1_TYPE=0',
                    'MOD1_VERSION=0.0']

        self.status_keys=[\
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


        self.conf_enable_keys=[\
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

        # fill fake controller buffers with fake data
        self.init_bufs(low=990,high=1010,size=self.image_bytes)

        self.init_frame()
        #self.set_frame(frame_info=frame_info)

    def init_bufs(self,low=990,high=1010,size=1):
        """ initialize each data buffer to random 8-bit integers i
            in range low to high, length size 
        """

        

        for index in range(0,self.num_buffers):
           self.buffers[index] = numpy.random.randint(low=low,high=high,\
                                 size=int(size/2),dtype=numpy.uint16)

    def update(self,bytes_per_pixel=None,amps_per_ccd=None,ccds_per_quad=None,data_type=None,\
                         pixelcount=None,linecount=None):

         """ update fake data parameters and given shape and format info """

         if data_type is not None:
           self.conf['data_type']=data_type

         if bytes_per_pixel is not None:
           self.conf['bytes_per_pixel']=bytes_per_pixel

         elif self.conf['data_type']==numpy.uint16:
           self.conf['bytes_per_pixel']=2

         if ccds_per_quad is not None:
           self.conf['ccds_per_quad']=ccds_per_quad

         if amps_per_ccd is not None:
           self.conf['amps_per_ccd']=amps_per_ccd 

         if linecount is not None:
           self.conf['linecount'] = linecount

         if pixelcount is not None:
           self.conf['pixelcount'] = pixelcount

         # make sure data_type and bytes per pixel are consistent
         a=numpy.dtype(self.conf['data_type'])
         b=a.itemsize
         if b != self.conf['bytes_per_pixel']:
            self.warn("fake bytes_per_pixel [%d] inconsistent with data_type [%s]" % (b,self.conf['data_type']))
            self.conf['bytes_per_pixel']=b

         n_pixels = self.conf['amps_per_ccd']*self.conf['ccds_per_quad']*\
                                     self.conf['linecount']*self.conf['pixelcount']

         n_bytes = n_pixels * self.conf['bytes_per_pixel']

         assert n_bytes <= self.image_bytes, \
              "image bytes [%d] exceeds fake buffer size[%d]" % (n_bytes,self.image_bytes)

         self.conf['n_bytes'] = n_pixels * self.conf['bytes_per_pixel']
         self.conf['fetch_time'] = FETCH_TIME * self.conf['n_bytes']/ self.image_bytes
         self.conf['readout_time'] = READOUT_TIME * self.conf['n_bytes']/ self.image_bytes

    #def stop_read(self):

    #    self.update_read()
    #    self.info("setting readout flag to False")


    def get_frame(self):

         """ return fake frame info which simulate actual controller data """

         try:
           if not self.status_lock.acquire(timeout=STATUS_LOCK_TIMEOUT):
              error_msg = "ERROR: failed to acquire status lock within %7.3f sec" %\
                   STATUS_LOCK_TIMEOUT
              self.warn(error_msg)
         except Exception as e:
              error_msg = "Exception acquiring status lock in get_frame: %s" % e
              self.warn(error_msg)

         f = self.frame_info

         try:
           self.status_lock.release()
         except Exception as e:
           error_msg = "Exception releasing status lock"
           self.warn(error_msg)

         return f

    def set_frame(self,frame_info = None):

         """ set infor for frame info which simulate actual controller data """

         try:
           if not self.status_lock.acquire(timeout=STATUS_LOCK_TIMEOUT):
              error_msg = "ERROR: failed to acquire status lock within %7.3f sec" %\
                   STATUS_LOCK_TIMEOUT
              self.warn(error_msg)
         except Exception as e:
           error_msg = "Exception acquiring status lock in set_frame %s" % e
           self.warn(error_msg)

         self.frame_info = frame_info

         try:
           self.status_lock.release()
         except Exception as e:
           error_msg = "Exception releasing status lock"
           self.warn(error_msg)



    def init_frame(self,t=None):
         """ 
         Initialize frame info required by LS4Controller.readout
         """

         if t is None:
            t=time.time()

         buffers = self.buf_indices

         frame_info = self.get_frame()

         #self.info("setting wbuf to 1")
         frame_info["wbuf"]=1   

         #self.info("setting all bufs to empty")

         for buf in buffers:
           frame_info[f"buf{buf}complete"] = 0
           frame_info[f"buf{buf}width"]=self.conf['pixelcount']*self.conf['amps_per_ccd']*self.conf['ccds_per_quad']
           frame_info[f"buf{buf}height"] = self.conf['linecount']
           frame_info[f"buf{buf}sample"] = 0
           frame_info[f"buf{buf}base"] = 0
           frame_info[f"buf{buf}pixels"] = 0
           frame_info[f"buf{buf}lines"] = 0
           frame_info[f"buf{buf}timestamp"] = t
           frame_info[f"buf{buf}sample"] = 0 
           frame_info[f"buf{buf}rawoffset"] = 0
           frame_info[f"buf{buf}rawblocks"] = 0
           frame_info[f"buf{buf}rawlines"] = 0

         self.t_read_start = t
         self.set_frame(frame_info=frame_info)

    def update_frame(self,t=None,buf_index=None,wbuf=None,complete=None):
         """ 
         update fake frame info required by LS4Controller.readout

         If wbuf != None , then update the value for the write-buf index as specified

         If  buf_index != None, update the record for the specified buffer index.
         If  buf_index = None, update the record for buf_index = wbuf

         complete determines how to modify the completeness state of the
         buffer. True/False  means set the completeness to 1/0 (Full/Empty).
         None means don't change the completeness state.

         t is the time stamp (None means use time.time() instead)

         """

         assert complete in [None,True,False],"unexpected value for complete: %s" % str(complete)
         if wbuf is not None:
           assert wbuf in self.buf_indices,"unexpected value for wbuf: %s" % str(wbuf)
         if buf_index is not None:
           assert buf_index in self.buf_indices,"unexpected value for buf_index: %s" % str(buf_index)
          
         if t is None:
            t=time.time()

         buffers = self.buf_indices


         frame_info = self.get_frame()

         if wbuf is not None:
            self.notifier("setting wbuf to %d " % wbuf)
            frame_info['wbuf']=wbuf

         if buf_index is None:
            buf = frame_info['wbuf']
         else:
            buf = buf_index

         if complete is None:
           pass
         elif complete:
           self.notifier("setting buf %d to complete" % buf)
           frame_info[f"buf{buf}complete"] = 1
         else:
           self.debug("setting buf %d to empty" % buf)
           frame_info[f"buf{buf}complete"] = 0
           frame_info[f"buf{buf}sample"] = 0
           frame_info[f"buf{buf}base"] = 0
           frame_info[f"buf{buf}pixels"] = 0
           frame_info[f"buf{buf}lines"] = 0
         
         frame_info[f"buf{buf}timestamp"] = t

         self.debug("setting frame to new frame_info")
         self.set_frame(frame_info=frame_info)
         self.debug("done setting frame to new frame_info")

    def update_read(self,t=None,waited=None):
       """ update the frame info emulated by Fake_Control. For each of the three
           buffers in the real controller, this is a record
           of the number of pixels and lines read so far from the CCD  and a 
           flag that is raised when  the CCD has been completely readout.

           t is the current system time, and waited the time (sec) since the
           readout began.
       """

       frame_info = self.get_frame()

       buffer_no = frame_info['wbuf']
       if t is None:
         t = time.time()

       if waited is None:
          waited = t - self.t_read_start


       lines = int((waited/self.conf['readout_time'])*self.conf['linecount'])

       if lines >= self.conf['linecount']:
          lines = self.conf['linecount']
          frame_info[f"buf{buffer_no}lines"] = lines
          frame_info[f"buf{buffer_no}complete"] = 1
       else:
          frame_info[f"buf{buffer_no}complete"] = 0
          frame_info[f"buf{buffer_no}lines"] = lines

       frame_info[f"buf{buffer_no}timestamp"] = t
        
       self.set_frame(frame_info=frame_info)  

    async def power(self, mode: bool | None = None):
        """Handles fake power to the CCD(s). Sets the fake power status bit.

        Parameters
        ----------
        mode
            If `None`, returns `True` if the array is currently powered,
            `False` otherwise. If `True`, powers n the array; if `False`
            powers if off.

        Returns
        -------
        state : `.ArchonPower`
            The power state as an `.ArchonPower` flag.

        """


        if mode is not None:
            #cmd_str = "POWERON" if mode is True else "POWEROFF"
            #cmd = await self.send_command(cmd_str, timeout=10)
            #if not cmd.succeeded():
            #    self.update_status([ControllerStatus.ERROR, ControllerStatus.POWERBAD])
            #    raise ArchonControllerError(
            #        f"Failed sending POWERON ({cmd.status.name})"
            #    )

            await asyncio.sleep(1)

            if mode is True:
              self.power_status = ArchonPower.ON
            else:
              self.power_status = ArchonPower.OFF

        return self.power_status


    def choose_buffer(self,frame_info=None, complete = None, latest=True):

        """  Of the all controller buffers that have specified completeness,
             return the index for the latest/earliest updatead for 
             latest = True, False
        """

        assert frame_info is not None,"frame_info is None"
        assert complete in [True,False], "complete must be True or False"
        assert latest in [True,False], "latest must be True or False"

        buffer_no = None

        # get list of buffer data (index,timestamp) with specified completeness
        buffers = [
            (n, frame_info[f"buf{n}timestamp"])
            for n in [1, 2, 3]
            if frame_info[f"buf{n}complete"] == int(complete)
        ]

        # make sure at least one buffer with required completeness exists
        if len(buffers) == 0:
            self.warn("There are no buffers with completeness %d" % int(complete))
          

        else:
            
            # sort the buffers by time stamp, high to low (latest = True) or
            # low to high (latest = False)
            sorted_buffers = sorted(buffers, key=lambda x: x[1], reverse=latest)

            # set buffer_no to first elemenry of the the first entry in the time sorted list

            buffer_no = sorted_buffers[0][0]

        return buffer_no

    async def check_buffer(self,frame_info=None,op=None):
        """ check if there is a controller buffer ready for fetching (op = 'fetch') or writing (op = 'write')"""

        buffer_no = None
        assert op in ['fetch','write']

        if op == 'fetch':
          # choose latest complete buffer
          complete = True
          latest = True
        else:
          # choose earliest empty buffer
          complete = False
          latest = False
 
        if frame_info is None:
            frame_info=self.get_frame()

        try:
          buffer_no = self.choose_buffer(frame_info=frame_info, complete=complete, latest=latest)
        except Exception as e:
          self.error("Exception checking for buffer ready for op = %s: %s" % (op,e))
  
        return buffer_no
