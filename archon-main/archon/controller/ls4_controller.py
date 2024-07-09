#
# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2021-01-19
# @Filename: archon.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)
#
# @Author: David Rabinowitz (david.rabinowitz@yale.edu)
# @Date: 2024-01-16
# @Filename: ls4_controller.py
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

"""
def test_parser():
    try:
      x=configparser.ConfigParser
      print("test of configparser: x = %s" % str(x))
      if x is None:
        print("configparser.ConfigParser returns none")
        return False
    except Exception as e:
      print("error instantiating ConfigParser: %s" % e)
      return False 

    return True
"""

from . import MAX_COMMAND_ID, MAX_CONFIG_LINES, FOLLOWER_TIMEOUT_MSEC, \
              P100_SUPPLY_VOLTAGE, N100_SUPPLY_VOLTAGE, AMPS_PER_CCD, \
              CCDS_PER_QUAD, STATUS_LOCK_TIMEOUT, BYTES_PER_PIXEL,\
              FETCH_TIME, READOUT_TIME, LINECOUNT, PIXELCOUNT, NUM_BUFS

#DEBUG
READOUT_TIME = 5 # for fake-controller testing

__all__ = ["LS4Controller","TimePeriod","Fake_Control"]

class TimePeriod():
    """ useful for keeping track of time intervals required for processes"""

    def __init__(self):

        self.start_time = 0.0
        self.end_time = 0.0
        self.period = 0.0

    def start(self):

        self.start_time=time.time()
        self.end_time = self.start

    def end(self):

        self.end_time = time.time()
        self.period = self.end_time-self.start_time

class Fake_Control():

    """ to keep to generate and keep track of fake data and parameters """


    def __init__(self, ls4_logger=None, notifier=None):

        self.count = 0
        self.power_status = None
        self.buffers = [None,None,None]
        self.conf={}
        self.num_buffers = 3
        self.buf_indices = list(range(1,self.num_buffers+1))
        self.image_bytes =  LINECOUNT*PIXELCOUNT*AMPS_PER_CCD*CCDS_PER_QUAD*BYTES_PER_PIXEL

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
        self.status_lock = threading.Lock()

        # house-keeping variable to simulate readout
        self.t_read_start = 0
        self.total_lines_read = 0
         
        # dictionary required by LS4Controller class
        self.frame_info = {}

        # fill fake controller buffers with fake data
        self.init_bufs(low=990,high=1010,size=self.image_bytes)

        # update additional fake-controller parameters.
        #
        self.update(bytes_per_pixel=BYTES_PER_PIXEL,\
                   data_type=numpy.uint16,\
                   amps_per_ccd=AMPS_PER_CCD,\
                   ccds_per_quad=CCDS_PER_QUAD,\
                   linecount=LINECOUNT,\
                   pixelcount=PIXELCOUNT)

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

        self.init_bufs(low=990,high=1010,size=self.image_bytes)

        self.init_frame()

    def init_bufs(self,low=990,high=1010,size=1):
        """ initialize each data buffer to random 8-bit integers i
            in range low to high, length size 
        """

        
        row_size = PIXELCOUNT*AMPS_PER_CCD*CCDS_PER_QUAD
        col_overscan = PIXELCOUNT- 1024
        row_overscan = LINECOUNT- 4096

        for index in range(0,self.num_buffers):
           self.buffers[index] = numpy.random.randint(low=low,high=high,\
                                 size=int(size/2),dtype=numpy.uint16)
           """
           for row in range(0,4096):
             amp_index = 0
             for ccd in range(0,CCDS_PER_QUAD):
               for amp in range(0,AMPS_PER_CCD):
                 i0 = (row*row_size)+(ccd*AMPS_PER_CCD*PIXELCOUNT)+(amp*PIXELCOUNT) 
                 if amp == 0:
                   i1 = i0
                   i2 = i0 + PIXELCOUNT - 1024
                   i3 = i2
                   i4 = i0 + PIXELCOUNT
                 else:
                   i1 = i0 + 1024
                   i2 = i0 + PIXELCOUNT
                   i3 = i0
                   i4 = i1
                 offset = (100*amp_index) 
                 numpy_offset = numpy.dtype('uint16').type(offset)
                 self.buffers[index][i3:i4] += numpy_offset
                 self.buffers[index][i1:i2] -= 20
                 amp_index += 1

           for row in range(4096,LINECOUNT):
             amp_index = 0
             for ccd in range(0,CCDS_PER_QUAD):
               for amp in range(0,AMPS_PER_CCD):
                 i0 = (row*row_size)+(ccd*AMPS_PER_CCD*PIXELCOUNT)+(amp*PIXELCOUNT) 
                 offset = (10*amp_index) - 20
                 numpy_offset = numpy.dtype('uint16').type(offset)
                 self.buffers[index][i0:i0+PIXELCOUNT] += numpy_offset
                 amp_index += 1
           """

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
           self.conf['linecount'] = LINECOUNT

         if pixelcount is not None:
           self.conf['pixelcount'] = PIXELCOUNT

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
           error_msg = "Exception acquiring status lock"
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
           error_msg = "Exception acquiring status lock"
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
           #self.info("setting buf %d to empty" % buf)
           frame_info[f"buf{buf}complete"] = 0
           frame_info[f"buf{buf}sample"] = 0
           frame_info[f"buf{buf}base"] = 0
           frame_info[f"buf{buf}pixels"] = 0
           frame_info[f"buf{buf}lines"] = 0
         
         frame_info[f"buf{buf}timestamp"] = t

         self.set_frame(frame_info=frame_info)

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


class LS4Controller(LS4_Device):
    """Talks to an Archon controller over TCP/IP.

    Parameters
    ----------
    name
        A name identifying this controller.
    host
        The hostname of the Archon.
    local_addr
        The (ip address,port) of the network interface  and port to use for connections (optional)
    port
        The port on which the Archon listens to incoming connections.
        Defaults to 4242.
    config
        Configuration data. Otherwise uses default configuration.
    """

    def __init__(
        self,
        name: str,
        host: str,
        local_addr: tuple = ('127.0.0.1',4242),
        port: int = 4242,
        config: dict | None = None,
        param_args: list[dict] | None = None,
        command_args: list[dict] | None = None,
        ls4_events: LS4_Events | None = None,
        ls4_logger: LS4_Logger | None = None,
        fake: bool | None = None,
        timing = None,
        notifier: Optional[Callable[[str], None]] = None,
    ):

        assert param_args is not None, "param_args are not specified"
        assert command_args is not None, "command_args are not specified"
        assert ls4_events is not None, "ls4_events are not specified"
        #assert test_parser(), "test of configparser fails"

        self.notifier_callback = notifier

        self.leader = False
        self.prefix = "follow %s" % name
        if ls4_logger is None:
           self.ls4_logger = LS4_Logger(name=name)
        else:
           self.ls4_logger=ls4_logger

        self.info = self.ls4_logger.info
        self.debug = self.ls4_logger.debug
        self.warn= self.ls4_logger.warn
        self.error= self.ls4_logger.error
        self.critical= self.ls4_logger.critical

        self.fake_controller = False
        self.fake_control = None
        if fake is not None:
           self.fake_controller = fake
  
        if self.fake_controller:     
           try:
             self.fake_control = Fake_Control(ls4_logger=self.ls4_logger)
           except Exception as e:
             error_msg = "Exception instantiating Fake_Control: %s" % e
             raise ArchonControllerError(error_msg)

        self.info("\n\tname: %s    host: %s    port: %d    local_addr: %s    fake: %s" %\
             (name,host,port,local_addr,fake))

        self.__running_commands: dict[int, ArchonCommand] = {}
        self._id_pool =  None
        self._reset_id_pool()
        LS4_Device.__init__(self, name=name, host=host, port=port, local_addr=local_addr,
                    ls4_logger=self.ls4_logger, fake = self.fake_controller)

        self.name = name
        self.host = host
        self._status: ControllerStatus = ControllerStatus.UNKNOWN
        self.__status_event = asyncio.Event()

        self._binary_reply: Optional[bytearray] = None

        self.auto_flush: bool | None = None

        self.parameters: dict[str, int] = {}

        self.current_window: dict[str, int] = {}
        self.default_window: dict[str, int] = {}

        self.config = config or lib_config
        self.acf_file: str | None = None

        #self.debug("instantiating acf_config")
        #self.acf_config: configparser.ConfigParser() | None = None
        self.acf_config =configparser.ConfigParser() 
        #self.debug("acf_config = %s" % str(self.acf_config))
        if self.acf_config is None:
           self.error("could not instantiate acf_config")

        # TODO: asyncio recommends using asyncio.create_task directly, but that
        # call get_running_loop() which fails in iPython.
        self._job = asyncio.get_event_loop().create_task(self.__track_commands())

        self.frame=None
      
        # addition by D. Rabinowitz follow here

        if "timeouts" not in self.config:
            self.config["timeouts"]={}

        self.config["timeouts"].update(\
            {"controller_connect": 5,\
            "write_config_timeout": 2,\
            "write_config_delay": 0.0001,\
            "expose_timeout": 2,\
            "readout_expected": 40,\
            "readout_max": 60,\
            "fetching_expected": 5,\
            "fetching_max": 10,\
            "flushing": 8.2,\
            "fast_flushing": 2.2,\
            "pneumatics": 1.5,\
            "purge": 0.2})

        if "supply voltages" not in self.config:
            self.config["supply voltages"]={}

        self.config["supply voltages"].update(\
               {"p5v_v":5.0,\
                "p6v_v":6.0,\
                "n6v_v":-6.0,\
                "p17v_v":17.0,\
                "n17v_v":-17.0,\
                "p35v_v":35.0,\
                #"n35v_v":-35.0,\
                # -35V line is not used, but registers as zero V ?
                "n35v_v":0.0,\
                #
                # Power Supply +/-100 lines changes to +/-50 v
                #"p100v_v":100.0,\
                #"n100v_v":-100.0\
                "p100v_v":P100_SUPPLY_VOLTAGE,\
                "n100v_v":N100_SUPPLY_VOLTAGE\
               })
             
        if "expose params" not in self.config:
            self.config["expose params"]={}

        self.config["expose params"].update(\
               {"date-obs":"0000-00-00T00:00:00",\
                "object": "TEST",\
                "obsmode": "TEST",\
                "imagetyp": "TEST",\
                "exptime": 0.0,\
                "focus": 0.0,\
                "tele-ra": 0.0,\
                "tele-dec": 0.0,\
                "chip-ra": 0.0,\
                "chip-dec": 0.0,\
                "equinox": 2000.0,\
                "lst": 0.0,\
                "ha": 0.0,\
                "filterna": "clear",\
                "filterid": "",\
                "frame": 0,\
                "read-per": 0.0,\
                "xbinning": 1,\
                "ybinning": 1,\
                "gain": 1.0,\
                "readnois": 0.0,\
                "ccdsec": "[1:1024,1:4096]",\
                "biassec": "[1024:1024,4096:4096]",\
                "bias": 0.0,\
                "ccdtemp": 0.0,\
                "fileroot": "",\
                "ujd": 0.0,\
                "fwhm": 0.0,\
                "sky": 0.0,\
                "skysigma": 0.0,\
                "zp": 0.0\
               })
             

        self.ls4_sync_io = LS4_SyncIO(name=self.name,ls4_events=ls4_events,
           param_args=param_args,command_args=command_args,ls4_logger = self.ls4_logger)
   
        self.set_sync_index=self.ls4_sync_io.set_sync_index
        self.set_sync=self.ls4_sync_io.set_sync

        if timing is not None:
           self.timing=timing
        else:
           self.timing={'expose':TimePeriod(),'readout':TimePeriod(),'fetch':TimePeriod()}

        # ned a mutex to lock self._status while changing status bits
        self.status_lock = threading.Lock()

        # Use a buffer_flag for each of the buffers in controller memory to indicate if its
        # is ready to be fetched or not (True,False). Intialize all the flags to False
        # at startup. After a controller has finished reading out out an image to a buffer,
        # set the flag to True (ready to be fetched). After the data in that buffer has been
        # fetched, the the flag to False (ready to be written, but not yet to be fetched).
 
        self.num_buffers = 3
        self.buf_indices = list(range(1,self.num_buffers+1))

    
    def notifier(self,str):
        if self.notifier_callback is not None:
           self.notifier_callback(str)
        else:
           pass

    def set_lead(self, lead_flag: bool = False):
         self.leader = lead_flag
         self.prefix = "leader %s" % self.name
         if self.ls4_sync_io is not None:
            self.ls4_sync_io.set_lead(lead_flag)

    async def start(self, reset: bool = True, read_acf: bool = True, acf_file = None,
                    sync_flag: bool | None = None):
        """Starts the controller connection. If ``reset=True``, resets the status."""

        await super().start()
        self.notifier(f"Controller {self.name} connected at {self.host}.")

        if read_acf:
           if self.fake_controller and acf_file is not None:
             self.notifier(f"Retrieving ACF data from acf_file {acf_file}.")
             self.acf_config = self.acf_file_to_parser(acf_file=acf_file)
           else:
             self.notifier(f"Retrieving ACF data from controller {self.name}.")
             config_parser, _ = await self.read_config(sync_flag=sync_flag)
             self.acf_config = config_parser
           self._parse_params()

        # disable shutter on power up
        self.shutter_enable=False

        if reset:
            try:
                await self._set_default_window_params()
                await self.reset(sync_flag=False)
            except ArchonControllerError as err:
                warnings.warn(f"Failed resetting controller: {err}", ArchonUserWarning)

        return self

    @property
    def status(self) -> ControllerStatus:
        """Returns the status of the controller as a `.ControllerStatus` enum type."""

        try:
          if not self.status_lock.acquire(timeout=STATUS_LOCK_TIMEOUT):
             error_msg = "ERROR: failed to acquire status lock within %7.3f sec" %\
                  STATUS_LOCK_TIMEOUT
             self.warn(error_msg)
        except Exception as e:
          error_msg = "Exception acquiring status lock"
          self.warn(error_msg)

        state = self._status
        try:
          self.status_lock.release()
        except Exception as e:
          error_msg = "Exception releasing status lock"
          self.warn(error_msg)

        return state

    async def is_idle(self):
        return await self.check_status(ControllerStatus.IDLE)

    async def is_exposing(self):
        return await self.check_status(ControllerStatus.EXPOSING)

    async def is_readout_pending(self):
        return await self.check_status(ControllerStatus.READOUT_PENDING)

    async def is_reading(self):
        return await self.check_status(ControllerStatus.READING)

    async def is_fetching(self):
        return await self.check_status(ControllerStatus.FETCHING)

    async def is_power_on(self):
        return await self.check_status(ControllerStatus.POWERON)

    async def is_power_bad(self):
        return await self.check_status(ControllerStatus.POWERBAD)

    async def check_status(
        self,
        bits: ControllerStatus | list[ControllerStatus],
        mode="or",
        wait_flag = False,
        max_wait_time = 0.0,
    ):

        """ check if any, none, or all (mode='or', 'nor', or 'and')
            of the specified status bits are set

            if wait_flag is True, wait up to max_wait_time sec for the
            status bits to change to the required value.

        """

        assert mode in ['or','nor','and'], \
          "mode must be in [or, nor, and]"

        if not isinstance(bits, (list, tuple)):
            bits = [bits]
         
        result = False

        # create as mask with only the specifed bits set to 1
        mask = ControllerStatus.CLEAR 
        for b in bits:
           mask |= b
  
        if wait_flag:

          # yield_status is a generator that returns the controller
          # status every time the status bits change. When the
          # returned status value matches the specified conditions
          # (bits and mode), or when max_wait_time is exceeded
          # the async for loop exits.

          status = None
          t_start = time.time()
          async for status in self.yield_status():
            result =  self.bitmask_logic(status_bits=status,mode=mode,mask=mask)
            dt = time.time() - t_start
            if result is True:
               break
            elif dt > max_wait_time:
               self.warn("timeout waiting %s sec for status to change to mask %d mode %s" % (int(mask),mode))
               break
            elif result is None:
               self.error("bitmask logic yields None")
               break

        else:
          status = self.status
          result =  self.bitmask_logic(status_bits=status,mode=mode,mask=mask)

        assert result is not None, "failed to apply mask logic"

        return result

    async def yield_status(self) -> AsyncIterator[ControllerStatus]:
        """Asynchronous generator yield the status of the controller."""

        prev_status = self.status
        yield prev_status # Yield the status on subscription to the generator.
        while True:
            await self.__status_event.wait()
            new_status = self.status
            if new_status != prev_status:
                yield new_status
                prev_status = new_status
            self.__status_event.clear()

    def bitmask_logic(self,status_bits = None, mode=None, mask=None):

        """ evaluate result of masking bits with given mode """

        try:
          assert mode in ['or','nor','and'], "mode must be in [or, nor, and]"
          assert status_bits is not None, "status_bits is None"
          assert mask is not None, "mask is None"
        except Exception as e:
          self.error("exception in bitmask_logic: %s" % e)
          return None

        if mode == 'or': 
           # return true if the mask and the status_bits have any non-zero bits in common
           if status_bits&mask:
              return True

        elif mode == 'nor':
           # return true if the mask and the status word have no non-zero bits in common
           if not (status_bits&mask):
             return True

        else:
           # return true if the mask and the status word have all non-zero mask bits in common
           if status_bits&mask == mask:
             return True

        return False


    def get_obsdate(self,tm=None):
        if tm is None:
           tm=time.gmtime()
        dt = "%04d-%02d-%02dT%02d:%02d:%05.2f" % \
              (tm.tm_year,tm.tm_mon,tm.tm_mday, tm.tm_hour,tm.tm_min,tm.tm_sec)
        return dt
        
    def update_status(
        self,
        bits: ControllerStatus | list[ControllerStatus],
        mode="on",
        notify=True,
    ):
        """Updates the status bitmask, allowing to turn on, off, or toggle a bit."""

        if not isinstance(bits, (list, tuple)):
            bits = [bits]

        # Check that we don't get IDLE and ACTIVE at the same time
        all_bits = ControllerStatus(0)
        for bit in bits:
            all_bits |= bit

        if (ControllerStatus.ACTIVE & all_bits) and (ControllerStatus.IDLE & all_bits):
            raise ValueError("Cannot set IDLE and ACTIVE bits at the same time.")

        status = self.status

        for bit in bits:
            if mode == "on":
                status |= bit
            elif mode == "off":
                status &= ~bit
            elif mode == "toggle":
                status ^= bit
            else:
                raise ValueError(f"Invalid mode '{mode}'.")
        # Make sure that we don't have IDLE and ACTIVE states at the same time.
        if ControllerStatus.IDLE in bits:
            status &= ~ControllerStatus.ACTIVE

        if status & ControllerStatus.ACTIVE:
            status &= ~ControllerStatus.IDLE
        else:
            status |= ControllerStatus.IDLE

        # Handle incompatible power bits.
        if ControllerStatus.POWERBAD in bits:
            status &= ~(ControllerStatus.POWERON | ControllerStatus.POWEROFF)
        elif ControllerStatus.POWERON in bits or ControllerStatus.POWEROFF in bits:
            status &= ~ControllerStatus.POWERBAD
            if ControllerStatus.POWERON in bits:
                status &= ~ControllerStatus.POWEROFF
            else:
                status &= ~ControllerStatus.POWERON

        # Remove UNKNOWN bit if any other status has been set.
        if status != ControllerStatus.UNKNOWN:
            status &= ~ControllerStatus.UNKNOWN

        try:
          if not self.status_lock.acquire(timeout=STATUS_LOCK_TIMEOUT):
             error_msg = "ERROR: failed to acquire status lock within %7.3f sec" %\
                  STATUS_LOCK_TIMEOUT
             self.warn(error_msg)
        except Exception as e:
          error_msg = "Exception acquiring status lock: %s" % e
          self.warn(error_msg)


        self._status = status
       
        try:
           self.status_lock.release()
        except Exception as e:
           error_msg = "Exception releasing status lock: %s" % e
           self.warn(error_msg)
      
        if notify:
            self.__status_event.set()

    def send_command(
        self,
        command_string: str,
        command_id: Optional[int] = None,
        sync_flag: bool | None = None,
        **kwargs,
    ) -> ArchonCommand:

        """version of send_command required by send_many() 

        Parameters
        ----------
        command_string
            The command to send to the Archon. Will be converted to uppercase.
        command_id
            The command id to associate with this message. If not provided, a
            sequential, autogenerated one will be used.
        kwargs
            Other keyword arguments to pass to `.ArchonCommand`.
        """

        command_id = command_id or self._get_id()
        #self.debug("non-async sending command,id [%s,%d] sync_flag: %s" %\
        #   (command_string,command_id,sync_flag))

        if command_id > MAX_COMMAND_ID or command_id < 0:
            raise ArchonControllerError(
                f"Command ID must be in the range [0, {MAX_COMMAND_ID:d}]."
            )

        command = ArchonCommand(
            command_string,
            command_id,
            controller=self,
            fake=self.fake_controller,
            **kwargs,
        )
        self.__running_commands[command_id] = command

        if self.fake_controller:
          self.fake_write(command.raw)
          command._mark_done()
        else:
          self.write(command.raw)
 
        return command

    async def send_many(
        self,
        cmd_strs: Iterable[str],
        max_chunk=100,
        timeout: Optional[float] = None,
        sync_flag: bool | None = None,
    ) -> tuple[list[ArchonCommand], list[ArchonCommand]]:
        """Sends many commands and waits until they are all done.

        def send(command_str or times out, cancels any future command. Returns a list
        of done commands and a list failed commands (empty if all the commands
        have succeeded). Note that ``done+pending`` can be fewer than the length
        of ``cmd_strs``.

        The order in which the commands are sent and done is not guaranteed. If that's
        important, you should use `.send_command`.

        Parameters
        ----------
        cmd_strs
            List of command strings to send. The command ids are assigned automatically
            from available IDs in the pool.
        max_chunk
            Maximum number of commands to send at once. After sending, waits until all
            the commands in the chunk are done. This does not guarantee that
            ``max_chunk`` of commands will be running at once, that depends on the
            available command ids in the pool.
        timeout
            Timeout for each single command.

        """

        # Copy the strings so that we can pop them. Also reverse it because
        # we'll be popping items and we want to conserve the order.
        cmd_strs = list(cmd_strs)[::-1]
        done: list[ArchonCommand] = []

        while len(cmd_strs) > 0:
            pending: list[ArchonCommand] = []
            if len(cmd_strs) < max_chunk:
                max_chunk = len(cmd_strs)
            if len(self._id_pool) >= max_chunk:
                cmd_ids = (self._get_id() for __ in range(max_chunk))
            else:
                cmd_ids = (self._get_id() for __ in range(len(self._id_pool)))
            for cmd_id in cmd_ids:
                cmd_str = cmd_strs.pop()
                cmd = self.send_command(command_string = cmd_str,\
                         command_id=cmd_id, timeout=timeout, sync_flag = sync_flag)
                pending.append(cmd)
            done_cmds: list[ArchonCommand] = await asyncio.gather(*pending)
            if all([cmd.succeeded() for cmd in done_cmds]):
                done += done_cmds
                for cmd in done_cmds:
                    self._id_pool.add(cmd.command_id)
            else:
                failed: list[ArchonCommand] = []
                for cmd in done_cmds:
                    if cmd.succeeded():
                        done.append(cmd)
                    else:
                        failed.append(cmd)
                return done, failed

        return (done, [])

    async def send_and_wait(
        self,
        command_string: str,
        raise_error: bool = True,
        sync_flag: bool | None = None,
        **kwargs,
    ):
        """Sends a command to the controller and waits for it to complete.

        Parameters
        ----------
        command_string
            The command to send to the Archon. Will be converted to uppercase.
        raise_error
            Whether to raise an error if the command fails. If `False`, a
            warning will be issued.
        kwargs
            Other arguments to be sent to `.send_command`.

        """

        command_string = command_string.upper()
        command = None
        error_msg = None

        #self.debug("start send_and_wait [%s]" % command_string)
        #self.debug("kwargs are: %s" % str(kwargs))

        try:
           #self.debug("async sending command [%s]" % command_string)
           command = await self.send_command(command_string = command_string, \
                     sync_flag = sync_flag, **kwargs)
           #self.debug("done async sending command [%s]" % command_string)
           if not command.succeeded():
              error_msg = "failed send_command [%s]" %\
                  command_string
        except Exception as e:
           error_msg= "exception sending command [%s]: %s" %\
               (command_string,e)

        if error_msg:
          self.error(error_msg)
          if raise_error:
             self.update_status(ControllerStatus.ERROR)
             raise ArchonControllerError(f"send_and_wait: Failed running {command_string}.")
          else:
             warnings.warn(f"send_and_wait: Failed running {command_string}.", \
                      ArchonUserWarning)

        #self.debug("done send_and_wait [%s]" % command_string)
        return command

    async def process_message(self, line: bytes) -> None:
        """Processes a message from the Archon and associates it with its command."""

        match = re.match(b"^[<|?]([0-9A-F]{2})", line)
        if match is None:
            warnings.warn(
                f"Received invalid reply {line.decode()}",
                ArchonControllerWarning,
            )
            return

        command_id = int(match[1], 16)
        if command_id not in self.__running_commands:
            warnings.warn(
                f"Cannot find running command for {line}",
                ArchonControllerWarning,
            )
            return

        self.__running_commands[command_id].process_reply(line)

    async def stop(self):
        """Stops the client and cancels the command tracker."""

        self._job.cancel()
        await super().stop()

    async def get_system(self, sync_flag = None) -> dict[str, Any]:
        """Returns a dictionary with the output of the ``SYSTEM`` command."""
        cmd = await self.send_command(command_string = "SYSTEM", timeout=5,\
                     sync_flag = sync_flag)
        if not cmd.succeeded():
            error = cmd.status == ArchonCommandStatus.TIMEDOUT
            raise ArchonControllerError(
                f"Command STATUS finished with status {cmd.status.name!r}",
                set_error_status=error,
            )

        system = {}

        if self.fake_controller:
          keywords=self.fake_control.system_keys
        else:
          keywords = str(cmd.replies[0].reply).split()

        for key, value in map(lambda k: k.split("="), keywords):
            system[key.lower()] = value
            if match := re.match(r"^MOD([0-9]{1,2})_TYPE", key, re.IGNORECASE):
                name_key = f"mod{match.groups()[0]}_name"
                system[name_key] = ModType(int(value)).name

        return system


    async def get_device_status(self, update_power_bits: bool = True,\
                                 sync_flag: bool | None = None) -> dict[str, Any]:
        """Returns a dictionary with the output of the ``STATUS`` command."""

        def check_int(s):
            if s[0] in ("-", "+"):
                return s[1:].isdigit()
            return s.isdigit()

        cmd = await self.send_command(command_string = "STATUS", timeout=5,
                  sync_flag = sync_flag)
        if not cmd.succeeded():
            error = cmd.status == ArchonCommandStatus.TIMEDOUT
            raise ArchonControllerError(
                f"Command STATUS finished with status {cmd.status.name!r}",
                set_error_status=error,
            )

        if not self.fake_controller:
          keywords = str(cmd.replies[0].reply).split()
          status = {
              key.lower(): int(value) if check_int(value) else float(value)
              for (key, value) in map(lambda k: k.split("="), keywords)
          }
        else:
          status = {'powergood':1,'overheat':0,'power':4}
          status_keys=self.fake_control.status_keys
          conf_enable_keys=self.fake_control.conf_enable_keys
          for k in status_keys:
              status[k]=0.0
          for k in conf_enable_keys:
              status[k]=0  

        if update_power_bits:
            await self.power(sync_flag = sync_flag)

        return status

    async def get_frame(self, sync_flag = None) -> dict[str, int]:
        """Returns the frame information.

        All the returned values in the dictionary are integers in decimal
        representation.
        """

        #cmd = await self.send_command(command_string = "FRAME", timeout=5,\
        cmd = await self.send_command(command_string = "FRAME", timeout=10,\
              sync_flag = sync_flag)
        if not cmd.succeeded():
            raise ArchonControllerError(
                f"Command FRAME failed with status {cmd.status.name!r}"
            )

        keywords = str(cmd.replies[0].reply).split()
        frame = {
            key.lower(): int(value) if "TIME" not in key else int(value, 16)
            for (key, value) in map(lambda k: k.split("="), keywords)
        }

        #print("get_frame: frame: %s" % str(frame))
        self.frame=frame
        return frame

    def print_frame(self,buf=None, frame=None):

        assert frame is not None, "frame is None"

        for b in self.buf_indices:
          if buf is None or buf == b:
             buf_str = "buf%d" % b
             for entry in frame:
                if buf_str in entry:
                  self.info("%s: %s" % (entry,str(frame[entry])))

        

    async def read_config(
        self,
        save: str | bool = False,
        sync_flag: bool | None = None
    ) -> tuple[configparser.ConfigParser, list[str]]:
        """Reads the configuration from the controller.

        Parameters
        ----------
        save
            Save the configuration to a file. If ``save=True``, the configuration will
            be saved to ``~/archon_<controller_name>.acf``, or set ``save`` to the path
            of the file to save.
        """

        key_value_re = re.compile("^(.+?)=(.*)$")

        def parse_line(line):
            match = key_value_re.match(line)
            assert match
            k, v = match.groups()
            # It seems the GUI replaces / with \ even if that doesn't seem
            # necessary in the INI format.
            k = k.replace("/", "\\")
            if ";" in v or "=" in v or "," in v:
                v = f'"{v}"'
            return k, v

        await self.send_command(command_string = "POLLOFF", sync_flag = sync_flag)

        cmd_strs = [f"RCONFIG{n_line:04X}" for n_line in range(MAX_CONFIG_LINES)]

        done, failed = await self.send_many(cmd_strs =  cmd_strs, max_chunk=100,\
                         timeout=0.5, sync_flag = sync_flag)

        await self.send_command(command_string = "POLLON", sync_flag = sync_flag)

        if len(failed) > 0:
            ff = failed[0]
            status = ff.status.name
            raise ArchonControllerError(
                f"An RCONFIG command returned with code {status!r}"
            )

        if any([len(cmd.replies) != 1 for cmd in done]):
            raise ArchonControllerError("Some commands did not get any reply.")

        lines = [str(cmd.replies[0]) for cmd in done]

        # Trim possible empty lines at the end.
        config_lines = "\n".join(lines).strip().splitlines()

        # The GUI ACF file includes the system information, so we get it.
        system = await self.get_system()

        c = configparser.ConfigParser()
        c.optionxform = str  # type: ignore  Make it case-sensitive
        c.add_section("SYSTEM")
        for sk, sv in system.items():
            if "_name" in sk.lower():
                continue
            sl = f"{sk.upper()}={sv}"
            k, v = parse_line(sl)
            c.set("SYSTEM", k, v)
        c.add_section("CONFIG")
        for cl in config_lines:
            k, v = parse_line(cl)
            c.set("CONFIG", k, v)

        if save is not False and save is not None:
            if isinstance(save, str):
                path = save
            else:
                path = os.path.expanduser(f"~/archon_{self.name}.acf")
            with open(path, "w") as f:
                c.write(f, space_around_delimiters=False)

        return (c, config_lines)

    async def hold_timing(self, sync_flag =  None):
        cmd = await self.send_command(command_string = "HOLDTIMING", \
                 timeout=1, sync_flag = sync_flag)
        if not cmd.succeeded():
          self.update_status(ControllerStatus.ERROR)
          raise ArchonControllerError(\
               f"Failed sending {cmd.command_string} ({cmd.status.name})")

    async def release_timing(self, sync_flag = None):
        cmd = await self.send_command(command_string = "RELEASETIMING", timeout=1,\
                        sync_flag = sync_flag)
        if not cmd.succeeded():
          self.update_status(ControllerStatus.ERROR)
          raise ArchonControllerError(\
               f"Failed sending {cmd.command_string} ({cmd.status.name})")

    def acf_file_to_parser(self,acf_file=None):

        cp = None
        if acf_file is not None:
          cp = configparser.ConfigParser()

          input = str(acf_file)
          if os.path.exists(input):
             cp.read(input)
          else:
             self.warn("acf_file [%s] does not exist" % acf_file)
        else:
             self.warn("acf_file is not specified")

        return cp


    async def write_config(
        self,
        input: str | os.PathLike[str] | None = None,
        applyall: bool = False,
        applysystem: bool = False,
        applymods: list[str] = [],
        poweron: bool = False,
        timeout: float | None = None,
        overrides: dict = {},
        trigger_opts: dict = {},
        #notifier: Optional[Callable[[str], None]] = None,
        release_timing: bool = True,
        reset: bool = True,
        sync_flag: bool | None = None,
    ):
        """Writes a configuration file to the contoller. Optionally write only trigger options.

        Parameters
        ----------
        input
            The path to the configuration file to load. It must be in INI format with
            a section called ``[CONFIG]``. It can also be a string containing the
            configuration itself.
        applyall
            Whether to run ``APPLYALL`` after successfully sending the configuration.
        applysystem
            Whether to run ``APPLYSYSTEM`` after successfully sending the trigger options
        applymods
            A list of apply commands to send to modules (e.g.,
            ``['LOADTIMING', 'APPLYMOD2']``).
        poweron
            Whether to run ``POWERON`` after successfully sending the configuration.
            Requires applyall=True or "applysystem=True.
        timeout
            The amount of time to wait for each command to succeed.  If `None`, reads
            the value from the configuration entry for
            ``timeouts.write_config_timeout``.
        overrides
            A dictionary with configuration lines to be overwritten. Must be a mapping
            of keywords to replace, including the module name (e.g.,
            ``MOD11/HEATERAP``), to the new values.
        trigger_opts
            A dictionary with trigger options to be overwritten. Must be a mapping
            of keywords to replace, e.g. {"TRIGOUTLEVEL":0, "TRIGOUTFORCE": 1'}
        release_timing
            If True, allow controller to start its timing script after writing config file.
            If False, and "hold_timing()" was previously executed, then the controller will 
            not start the timing script until "release_timing()" is later
            executed. THis allow controllers connected by sync cables to synchronize their
            execution of their timing scripts.
        reset
            IF True/False reset after writing configuration
        """

        #self.debug("start write_config")
        ACS = ArchonCommandStatus

        timeout = timeout or self.config["timeouts"]["write_config_timeout"]
        delay: float = self.config["timeouts"]["write_config_delay"]

        poll_on = True

        if input is not None:
          #self.debug("instantiating ConfigParser from file %s" % input)
          cp = configparser.ConfigParser()

          input = str(input)
          if os.path.exists(input):
              cp.read(input)
          else:
              cp.read_string(input)

          if not cp.has_section("CONFIG"):
              raise ArchonControllerError(
                  "The config file does not have a CONFIG section."
              )

          # Undo the INI format: revert \ to / and remove quotes around values.
          aconfig = cp["CONFIG"]
          lines = []
          for key in aconfig:
              lines.append(key.upper().replace("\\", "/") + "=" + aconfig[key].strip('"'))


          #self.debug("Clearing previous configuration")
          try:
             #self.debug("start send_and_wait CLEARCONFIG")
             cmd = await self.send_and_wait(command_string = "CLEARCONFIG", \
                    timeout=timeout, sync_flag=sync_flag)
             #self.debug("done start send_and_wait CLEARCONFIG")
             if cmd is None or not cmd.succeeded():
                self.error("send_and_wait failed for CLEARCONFIG")
                raise ArchonControllerError(
                  "send_and_wait failed for CLEARCONFIG"
                )

          except Exception as e:
             self.error("exception send_and_wait CLEARCONFIG: %s" % e)
             raise ArchonControllerError(
               "exception send_and_wait CLEARCONFIG: %s" % e
             )
      

          #self.debug("sending configuration lines")

          # Stop the controller from polling internally to speed up network response
          # time. This command is not in the official documentation.
          await self.send_command(command_string = "POLLOFF",sync_flag = sync_flag)
          poll_on = False

          cmd_strs = [f"WCONFIG{n_line:04X}{line}" for n_line, line in enumerate(lines)]
          index = 1
          num_lines = len(cmd_strs)
          #self.debug("num_lines = %d" % num_lines)
          for line in cmd_strs:
              #self.debug("sending line %d/%d : %s" % (index,num_lines,line))   
              cmd = await self.send_command(command_string = line,\
                            timeout=timeout,sync_flag=sync_flag)
              if cmd.status == ACS.FAILED or cmd.status == ACS.TIMEDOUT:
                  self.update_status(ControllerStatus.ERROR)
                  await self.send_command(command_string = "POLLON",sync_flag=sync_flag)
                  poll_on = True
                  raise ArchonControllerError(
                      f"Failed sending line {cmd.raw!r} ({cmd.status.name})"
                  )
              await asyncio.sleep(delay)
              index += 1
          #self.debug("done sending configuration lines")
          self.acf_config = cp
          self.acf_file = input if os.path.exists(input) else None

        # Write MOD overrides. Do not apply since we optionall do an APPLYALL afterwards.
        if overrides and len(overrides) > 0:
           #self.debug("writing configuration overrides")
           for keyword, value in overrides.items():
             await self.write_line(keyword = keyword, value = value, apply=False, sync_flag = sync_flag)

        # Write trigger options, if any

        if trigger_opts and len(trigger_opts)>0:
          #self.debug("writing trigger options")
          for keyword, value in trigger_opts.items():
              await self.write_line(keyword = keyword, value = value, \
                       apply=False, sync_flag = sync_flag)
          #self.debug("done writing trigger options")

        # Restore polling
        if not poll_on:
          #self.debug("sending POLLON")
          await self.send_command(command_string ="POLLON",\
                         sync_flag=sync_flag)
          poll_on = True
          #self.debug("done sending POLLON")

        #self.debug("writing applymods")
        for mod in applymods:
            await self.send_and_wait(command_string=mod.upper(), \
                       timeout=5,sync_flag=sync_flag)
        #self.debug("done writing applymods")

        if applysystem:
            #self.debug("sending APPLYSYSTEM")
            await self.send_and_wait(command_string = "APPLYSYSTEM", \
                           timeout=5,sync_flag=sync_flag)
            #self.debug("done sending APPLYSYSTEM")

        elif applyall:
            #self.debug("sending APPLYALL")
            await self.send_and_wait(command_string = "APPLYALL", \
                        timeout=5,sync_flag=sync_flag)
            #self.debug("done sending APPLYALL")


            # Reset objects that depend on the configuration file.
            #self.debug("parsing params")
            self._parse_params()
            #self.debug("setting default window params")
            await self._set_default_window_params()
            #self.debug("done setting default window params")

            if poweron:
                self.notifier("sending POWERON") 
                await self.power(mode = True, sync_flag = sync_flag)
                #self.debug("done sending POWERON") 

        if reset:
          #self.debug("resetting")
          await self.reset(release_timing=release_timing,sync_flag=False)
          #self.debug("done resetting")

        self._reset_id_pool()
        #self.debug("done with write_config")
        return

    async def write_line(
        self,
        keyword: str,
        value: int | float | str,
        mod: Optional[str] = None,
        apply: bool | str = True,
        sync_flag: bool | None = None,
    ):
        """Write a single line to the controller, replacing the current configuration.

        Parameters
        ----------
        keyword
            The config keyword to replace. If ``mod=None``, must include the module
            name (e.g., ``MOD11/HEATERAP``); otherwise the module is added from
            ``mod``. Modules and module keywords can be separated by slashes or
            backlashes.
        value
            The value of the keyword.
        mod
            The name of the keyword module, e.g., ``MOD11``.
        apply
            Whether to re-apply the configuration for the module. If ``apply``
            is a string, defines the command to be used to apply the new setting,
            e.g., ``APPLYCDS``.

        """

        if not self.acf_config:
            raise ArchonControllerError("The controller ACF configuration is unknown.")

        keyword = keyword.upper().replace("/", "\\")

        if mod != "" and mod is not None:
            mod = mod.upper()
            if not keyword.startswith(mod):
                keyword = mod + "\\" + keyword
        else:
            mod_re = re.match(r"(MOD[0-9]+)\\", keyword)
            if mod_re:
                mod = mod_re.group(1)

        current_keywords = [k.upper() for k in list(self.acf_config["CONFIG"])]

        if keyword not in current_keywords:
            raise ArchonControllerError(f"Invalid keyword {keyword}")

        n_line = current_keywords.index(keyword)

        if isinstance(value, (int, float)):
            value_str = str(value)
        elif isinstance(value, str):
            if any(quotable_char in value for quotable_char in [",", " ", "="]):
                value_str = '"' + value + '"'
            else:
                value_str = value

        # For WCONFIG we need to use MODX/KEYWORD.
        keyword_wconfig = keyword.replace("\\", "/")
        line = f"{keyword_wconfig}={value_str}"

        cmd = await self.send_command(command_string = f"WCONFIG{n_line:04X}{line}", \
                   sync_flag=sync_flag)
        if cmd.status == ArchonCommandStatus.FAILED:
            raise ArchonControllerError(
                f"Failed sending line {cmd.raw!r} ({cmd.status.name})"
            )

        self.acf_config["CONFIG"][keyword] = value_str

        if apply:
            if isinstance(apply, str):
                apply_cmd_str = apply.upper()
            else:
                if mod is None:
                    raise ArchonControllerError("Apply can only be used with modules.")
                modn = mod[3:]
                apply_cmd_str = f"APPLYMOD{modn}"

            cmd_apply = await self.send_command(command_string = apply_cmd_str,\
                   sync_flag = sync_flag)
            if cmd_apply.status == ArchonCommandStatus.FAILED:
                raise ArchonControllerError(f"Failed applying changes to {mod}.")

            #self.debug(f"{keyword}={value_str}")

    async def power(self, mode: bool | None = None, sync_flag: bool | None = None):
        """Handles power to the CCD(s). Sets the power status bit.

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

        if self.fake_controller:
           power_status= await self.fake_control.power(mode)

           if power_status == ArchonPower.ON:
               self.update_status(ControllerStatus.POWERON)
           else:
               self.update_status(ControllerStatus.POWEROFF)

           return power_status


        power_status = None
        status = {}

        if mode is not None:
            cmd_str = "POWERON" if mode is True else "POWEROFF"
            cmd = await self.send_command(command_string = cmd_str, timeout=10,\
                            sync_flag = sync_flag)
            if not cmd.succeeded():
                self.update_status([ControllerStatus.ERROR, ControllerStatus.POWERBAD])
                raise ArchonControllerError(
                    f"Failed sending POWERON ({cmd.status.name})"
                )

            await asyncio.sleep(1)

        else:
            status = await self.get_device_status(update_power_bits=False)
            power_status = ArchonPower(status["power"])

        if (
            power_status not in [ArchonPower.ON, ArchonPower.OFF]
            or status["powergood"] == 0
        ):
            if power_status == ArchonPower.INTERMEDIATE:
                warnings.warn("Power in INTERMEDIATE state.", ArchonUserWarning)
            self.update_status(ControllerStatus.POWERBAD)
        else:
            if power_status == ArchonPower.ON:
                #self.debug("updating status to POWERON")
                self.update_status(ControllerStatus.POWERON)
            elif power_status == ArchonPower.OFF:
                #self.debug("updating status to POWEROFF")
                self.update_status(ControllerStatus.POWEROFF)

        return power_status

    async def set_autoflush(self, mode: bool, sync_flag: bool | None = None):
        """Enables or disables autoflushing."""

        self.notifier("setting ContinuousExposures: %s" % mode)
        await self.set_param(param = "ContinuousExposures", value = int(mode),\
              sync_flag = sync_flag)

        self.auto_flush = mode

    async def force_shutter_open(self, sync_flag = None):
        """ Force shutter open, even when controller is idle """

        self.notifier("forcing shutter open")
        await self.write_config(trigger_opts={"TRIGOUTLEVEL":1,"TRIGOUTFORCE":1},\
               applysystem=True,reset=False, sync_flag = sync_flag)

    async def force_shutter_close(self, sync_flag = None):
        """ Force shutter closed, even when controller is idle """

        self.notifier("forcing shutter closed")
        await self.write_config(trigger_opts={"TRIGOUTLEVEL":0,"TRIGOUTFORCE":1},\
               applysystem=True,reset=False, sync_flag = sync_flag)

    async def enable_shutter(self, sync_flag = None):
        """ Enable shutter during exposures """

        self.notifier("enabling exposure shutter")
        await self.write_config(trigger_opts={"TRIGOUTLEVEL":1,"TRIGOUTFORCE":0},\
               applysystem=True,reset=False, sync_flag = sync_flag)

    async def disable_shutter(self, sync_flag = None):
        """ Disable shutter during exposures """

        self.notifier("disabling exposure shutter")
        await self.write_config(trigger_opts={"TRIGOUTLEVEL":0,"TRIGOUTFORCE":1},\
               applysystem=True,reset=False, sync_flag = sync_flag)


    async def reset(self, autoflush=True, release_timing=True, \
                     update_status=True, sync_flag=None):
        """Resets timing and discards current exposures."""

        if sync_flag is None:
           sync_flag = self.ls4_sync_io.sync_flag

        self._parse_params()

        self.notifier(f"start resetting controller")

        #self.debug(f"hold_timing")
        await self.hold_timing()

        #self.debug(f"set autoflush %s" % autoflush)
        await self.set_autoflush(mode =autoflush,sync_flag = sync_flag)
        #self.debug(f"setting Exposures to 0")
        await self.set_param(param="Exposures", value=0, sync_flag=sync_flag)
        #self.debug(f"setting ReadOut to 0")
        await self.set_param(param="ReadOut", value=0, sync_flag=sync_flag)
        #self.debug(f"setting AbortExposure to 0")
        await self.set_param(param="AbortExposure", value=0, sync_flag=sync_flag)
        #self.debug(f"setting DoFlush to 0")
        await self.set_param(param="DoFlush", value=0, sync_flag=sync_flag)
        #self.debug(f"setting WaitCount to 0")
        await self.set_param(param="WaitCount", value=0, sync_flag=sync_flag)

        if self.shutter_enable:
           #self.debug("enabling shutter")
           await self.enable_shutter(sync_flag=sync_flag)
        else:
           #self.debug("disabling shutter")
           await self.disable_shutter(sync_flag = sync_flag)

        # Reset parameters to their default values.
        if "default_parameters" in self.config["archon"]:
            default_parameters = self.config["archon"]["default_parameters"]
            for param in default_parameters:
                #self.debug(f"setting %s to %d" %\
                #     (param, default_parameters[param]))
                await self.set_param(param=param, \
                      value=default_parameters[param], sync_flag=sync_flag)

        if release_timing:
            #self.debug(f"release_timing .")
            await self.release_timing()

        if update_status:
            #self._status = ControllerStatus.IDLE
            self.update_status (ControllerStatus.IDLE)
            #self.debug(f"awaiting self.power()")
            await self.power()  # Sets power bit.

        #self.debug(f"done with reset")

    def _parse_params(self):
        """Reads the ACF file and constructs a dictionary of parameters."""

        if not self.acf_config:
            raise ArchonControllerError("ACF file not loaded. Cannot parse parameters.")

        # Dump the ACF ConfigParser object into a dummy file and read it as a string.
        f = io.StringIO()
        self.acf_config.write(f)

        f.seek(0)
        data = f.read()

        matches = re.findall(
            r'PARAMETER[0-9]+\s*=\s*"([A-Z]+)\s*=\s*([0-9]+)"',
            data,
            re.IGNORECASE,
        )

        self.parameters = {k.upper(): int(v) for k, v in dict(matches).items()}

    
    async def _set_default_window_params(self, reset: bool = True):
        """Sets the default window parameters.

        This is assumed to be called only after the default ACF has been loaded
        and before any calls to `.write_line` or `.set_param`. Resets the window.

        """
        linecount = int(self.parameters.get("LINECOUNT", -1))
        pixelcount = int(self.parameters.get("PIXELCOUNT", -1))
        lines = int(self.parameters.get("LINES", -1))
        pixels = int(self.parameters.get("PIXELS", -1))
        preskiplines= int(self.parameters.get("PRESKIPLINES", 0))
        postskiplines = int(self.parameters.get("POSTSKIPLINES", 0))
        preskippixels = int(self.parameters.get("PRESKIPPIXELS", 0))
        postskippixels = int(self.parameters.get("POSTSKIPPIXELS", 0))
        overscanpixels = int(self.parameters.get("OVERSCANPIXELS", 0))
        overscanlines = int(self.parameters.get("OVERSCANLINES", 0))
        hbin = int(self.parameters.get("HORIZONTALBINNING", 1))
        vbin = int(self.parameters.get("VERTICALBINNING", 1))

        self.default_window = {
            "linecount": linecount,
            "pixelcount": pixelcount,
            "lines": lines,
            "pixels": pixels,
            "preskiplines": preskiplines,
            "postskiplines": postskiplines,
            "preskippixels": preskippixels,
            "postskippixels": postskippixels,
            "overscanpixels": overscanpixels,
            "overscanlines": overscanlines,
            "hbin": hbin,
            "vbin": vbin,
        }

        new_linecount = (preskiplines+lines+postskiplines+overscanlines) // vbin
        new_pixelcount = (preskippixels+pixels+postskippixels+overscanpixels) // hbin

        if new_linecount != linecount:
           self.warn("default linecount [%d] inconsistent with default preskip,postskip,lines,overscan [%d,%d,%d,%d]" %\
                     (linecount, preskiplines,postskiplines,lines,overscanlines))
           self.default_window["linecount"] =  new_linecount

        if new_pixelcount != pixelcount:
           self.warn("default pixelcount [%d] inconsistent with default preskip,postskip,pixel,overscan [%d,%d,%d,%d]" %\
                     (pixelcount,preskippixels,postskippixels,pixels,overscanpixels))
           self.default_window["pixelcount"] = new_pixelcount 
            

        self.current_window = self.default_window.copy()

        if self.fake_controller:
             self.fake_control.update(linecount=new_linecount, pixelcount=new_pixelcount)

        if reset:
            await self.reset_window()
       
    async def set_param(
        self,
        param: str,
        value: int,
        force: bool = False,
        sync_flag: bool | None = None
    ) -> ArchonCommand | None:

        """sets the parameter ``param`` to value ``value`` calling ``FASTLOADPARAM``.
           If self.ls4_sync_io.sync_flag is true, ls4_sync_io is used to synchronize
           execution of set_param across synchronized controllers

        """

        error_msg = None
        sync_test = False
        cmd = None
        prefix = self.prefix

        if sync_flag is None:
           sync_flag = self.ls4_sync_io.sync_flag

        if param in ["SYNCTEST","SYNC_TEST"]:
           sync_test = True

        #self.debug("%s: setting [%s] to [%d] sync_flag: %s sync_test: %s" %\
        #   (prefix,param,value,sync_flag,sync_test))

        # First we check if the parameter actually exists.
        if len(self.parameters) == 0:
            if self.acf_config is None:
                raise ArchonControllerError("ACF not loaded. Cannot modify parameters.")

        param = param.upper()
          
        if (not sync_test) and (param not in self.parameters) and (force is False):
            error_msg = f"Trying to set unknown parameter {param}"

        if sync_flag and error_msg is None:
          # The leader breezes through sync_prepare without waiting for events.
          # The followers get held up in sync prepare until the leader executes sync_update (below)

          #self.debug("%s preparing sync" % prefix)
          try:
            await self.ls4_sync_io.sync_prepare(param_args={'param':param,\
                               'value':value,'force':force},command_args=None)
          except Exception as e:
            error_msg = "Exception preparing sync: %s" % e

          # The leaders execute FASTPREPARM before the followers because it gets here first
          if not error_msg and not sync_test:

            #self.debug("%s sending FASTPREPPARAM" % prefix)
            cmd = await self.send_command(\
                           command_string = f"FASTPREPPARAM {param} {value}",\
                           sync_flag=False)
            if not cmd.succeeded():
               error_msg = "%s failed preparing parameters %s to %s" % (prefix,param,value)

          # Here the leader allows the followers to catch up and send FASTPREPPARAM command
          if not error_msg:
            #self.debug("%s updating sync with param_flag = True" % prefix)
            try:
              await self.ls4_sync_io.sync_update(param_flag=True)
            except Exception as e:
              error_msg = "Exception updating sync with param_flag = True: %s" % e

        # All the controller threads arrive here about the same time. However, if they
        # have been set up for synchronous IO, they will load the parameter at the same 
        # time. If they are not synchronized, the relative timing will be random.
        if not error_msg and not sync_test:
          cmd_string=f"FASTLOADPARAM {param} {value}"
          #self.debug("%s sending command [%s]" % (prefix,cmd_string))
          try:
            #cmd = await self.send_command(f"FASTLOADPARAM {param} {value}")
            cmd = await self.send_command(command_string = cmd_string, \
                           sync_flag = sync_flag)
            if not cmd.succeeded():
               error_msg = f"Failed sending command [%s]" % cmd_string
          except Exception as e:
            error_msg = "Exception setting param: %s" % e

        # synchronization house-keeping
        if not error_msg and sync_flag:
          try:
            #self.debug("%s verifying sync" % prefix)
            await self.ls4_sync_io.sync_verify(param_flag=True)
          except Exception as e:
            error_msg = "Exception verifying sync: %s" % e

        if error_msg is not None:
           self.error("%s: %s" % (prefix,error_msg))
           raise ArchonControllerError(f"Failed setting param {param} to value {value}:  %s" % error_msg)

        self.parameters[param] = value
        #self.debug("%s: done setting [%s] to [%d] sync_flag: %s sync_test: %s" %\
        #   (prefix,param,value,sync_flag,sync_test))
        
        return cmd

    async def reset_window(self):
        """Resets the exposure window."""
    
        await self.set_window(**self.default_window)

    async def set_window(
        self,
        linecount: int | None = None,
        pixelcount: int | None = None,
        lines: int | None = None,
        pixels: int | None = None,
        preskiplines: int | None = None,
        postskiplines: int | None = None,
        preskippixels: int | None = None,
        postskippixels: int | None = None,
        overscanlines: int | None = None,
        overscanpixels: int | None = None,
        hbin: int | None = None,
        vbin: int | None = None,
        sync_flag: bool | None = None,
    ):
        """Sets the CCD window."""

        if linecount is None:
            linecount = self.current_window["linecount"]

        if pixelcount is None:
            pixels = self.current_window["pixelcount"]

        if lines is None:
            lines = self.current_window["lines"]

        if pixels is None:
            pixels = self.current_window["pixels"]

        if preskiplines is None:
            preskiplines = self.current_window["preskiplines"]

        if postskiplines is None:
            postskiplines = self.current_window["postskiplines"]

        if preskippixels is None:
            preskippixels = self.current_window["preskippixels"]

        if postskippixels is None:
            postskippixels = self.current_window["postskippixels"]

        if overscanlines is None:
            overscanlines = self.current_window["overscanlines"]

        if overscanpixels is None:
            overscanpixels = self.current_window["overscanpixels"]

        if vbin is None:
            vbin = self.current_window["vbin"]

        if hbin is None:
            hbin = self.current_window["hbin"]

        new_linecount = (preskiplines+lines+postskiplines+overscanlines) // vbin
        new_pixelcount = (preskippixels+pixels+postskippixels+overscanpixels) // hbin

        if new_linecount != linecount:
           self.warn("current linecount [%d] inconsistent with default preskip,postskip,lines,overscan [%d,%d,%d,%d]" %\
                     (linecount, preskiplines,postskiplines,lines,overscanlines))
           linecount = new_linecount

        if new_pixelcount != pixelcount:
           self.warn("current pixelcount [%d] inconsistent with default preskip,postskip,pixel,overscan [%d,%d,%d,%d]" %\
                     (pixelcount, preskippixels,postskippixels,pixels,overscanpixels))
           pixelcount = new_pixelcount
            

        if lines >= 0:
            await self.set_param(param = "Lines", value = lines, sync_flag = sync_flag)
        else:
            warnings.warn("Lines value unknown. Did not set.", ArchonUserWarning)

        if pixels >= 0:
            await self.set_param(param = "Pixels", value = pixels, sync_flag = sync_flag)
        else:
            warnings.warn("Pixels value unknown. Did not set.", ArchonUserWarning)

        await self.set_param(param = "Pixels", value = pixels, sync_flag = sync_flag)
        await self.set_param(param ="PreSkipLines", value = preskiplines, sync_flag = sync_flag)
        await self.set_param(param ="PostSkipLines", value = postskiplines, sync_flag = sync_flag)
        await self.set_param(param ="PreSkipPixels", value = preskippixels, sync_flag = sync_flag)
        await self.set_param(param ="PostSkipPixels", value = postskippixels, sync_flag = sync_flag)
        await self.set_param(param ="VerticalBinning", value = vbin, sync_flag = sync_flag)
        await self.set_param(param ="HorizontalBinning", value = hbin, sync_flag = sync_flag)
        await self.write_line(keyword = "LINECOUNT", value = linecount, apply=False, sync_flag = sync_flag)
        await self.write_line(keyword = "PIXELCOUNT", value = pixelcount, apply="APPLYCDS", sync_flag = sync_flag)

        self.current_window = {
            "linecount": linecount,
            "pixelcount": pixelcount,
            "lines": lines,
            "pixels": pixels,
            "preskiplines": preskiplines,
            "postskiplines": postskiplines,
            "preskippixels": preskippixels,
            "postskippixels": postskippixels,
            "overscanpixels": overscanpixels,
            "overscanlines": overscanlines,
            "hbin": hbin,
            "vbin": vbin,
        }


        return self.current_window


    async def expose(
        self,
        exposure_time: float = 1,
        readout: bool = True,
        sync_flag: bool | None = None,
    ) -> asyncio.Task:
        """Integrates the CCD for ``exposure_time`` seconds.

        Returns immediately once the exposure has begun. If ``readout=False``, does
        not trigger a readout immediately after the integration finishes. The returned
        `~asyncio.Task` waits until the integration is done and, if ``readout``, checks
        that the readout has started.
        """

        if readout:
          assert not self.fake_controller,\
             "the code does not handle the case readout=True whe fake_controller is True"
               
        if sync_flag is None:
           sync_flag = self.ls4_sync_io.sync_flag

        #self.notifier(f"%s: preparing for exposure duration exposure {exposure_time} " % self.get_obsdate())

        CS = ControllerStatus

        if not await self.is_power_on():
            raise ArchonControllerError("Controller power is off.")
        elif await self.is_power_bad():
            raise ArchonControllerError("Controller power is invalid.")
        elif not  await self.is_idle():
            raise ArchonControllerError("The controller is not idle.")
        elif await self.is_readout_pending():
            raise ArchonControllerError(
                "Controller has a readout pending. Read the device or flush."
            )


        await self.reset(autoflush=False, release_timing=False,sync_flag=False)
        if sync_flag:
           #self.info(f"syncing up")
           await self.set_param(param="SYNCTEST",value=0, sync_flag = sync_flag)

        # Set integration time in centiseconds (yep, centiseconds).
        #self.debug(f"setting IntCS to %d" % int(exposure_time * 100))
        await self.set_param(param = "IntCS", value = int(exposure_time * 100),\
                     sync_flag = sync_flag)

        if readout is False:
            #self.debug(f"skipping readout: setting Readout param to 0")
            await self.set_param(param = "ReadOut", value = 0, sync_flag = sync_flag)
        else:
            #self.debug(f"reading out: setting Readout param to 1")
            await self.set_param(param = "ReadOut", value=1, sync_flag = sync_flag)

        #self.info(f"setting Exposures to 1")
        await self.set_param(param = "Exposures", value = 1, sync_flag = sync_flag)

        self.config['expose params']['exptime']=0.0
        self.config['expose params']['read-per']=0.0

        #self.info(f"sending RELEASETIMING")
        await self.send_command(command_string = "RELEASETIMING", sync_flag = sync_flag)
        #self.info(f"updating status to EXPOSING and READOUT_PENDING")
        self.update_status([CS.EXPOSING, CS.READOUT_PENDING])
        #self.info(f"done updating status to EXPOSING and READOUT_PENDING")
        self.timing['expose'].start()
        tm = time.gmtime()
        self.config['expose params']['date-obs']=self.get_obsdate(tm)
        self.config['expose params']['startobs']=self.get_obsdate(tm)

        #self.notifier(f"%s: starting exposure of duration exposure {exposure_time} " % self.get_obsdate())
        async def update_state():
           dt = 0.0
           done=True
           aborted=False
           tm = time.gmtime()
           t_start=time.time()
           if exposure_time>0.0 and dt < exposure_time:
              #self.notifier(f"%s: waiting %7.3f sec for exposure to end" %\
              #    (self.get_obsdate(),exposure_time))
              done = False
              aborted = False
              while (not done) and (not aborted):
                 if dt >= exposure_time:
                    #self.notifier(f"update_state: end %s:  exposure completed after %7.3f sec" % (self.get_obsdate(tm),dt))
                    done= True
                 elif not await self.is_exposing():  # Must have been aborted.
                    self.warn(f"update_state: exposure was aborted after %7.3f sec" % dt)
                    aborted=True
                 else:
                    await asyncio.sleep(0.01)
                    dt = time.time()-t_start
                    tm = time.gmtime()
           else:
              pass
              #self.debug(f"update_state: skipping 0-sec exposure loop")

           self.timing['expose'].end()
           self.config['expose params']['exptime']=self.timing['expose'].period
           self.config['expose params']['doneobs']=self.get_obsdate(tm)
           self.update_status(CS.EXPOSING, 'off')
           if done and not aborted:
              #self.debug(f"update_state: updating status to READOUT_PENDING")
              self.update_status(CS.READOUT_PENDING)
           #self.notifier(f"%s: done with exposure of duration exposure {exposure_time} " % self.get_obsdate())
            
           if done:
              if readout: # readout now
                 #self.notifier(f"update_state: starting readout")
                 self.update_status( CS.READOUT_PENDING, 'off')
                 self.update_status(CS.READING)
                 self.timing['readout'].start()
                 frame = await self.get_frame()
                 self.update_status(CS.READING,'off')
                 wbuf = frame["wbuf"]
                 if frame[f"buf{wbuf}complete"] == 0:
                    self.timing['readout'].end()
                    self.config['expose params']['read-per']=self.timing['readout'].period
                 else:
                    self.error(f"update_state: failed starting readout")
                    raise ArchonControllerError("Controller is not reading.")

        #self.debug(f"%s: returning awaited update_state function" % self.get_obsdate(time.gmtime()))
        return await update_state()

    async def abort(self, readout: bool = False, sync_flag: bool | None = None):
        """Aborts the current exposure.

        If ``readout=False``, does not trigger a readout immediately after aborting.
        Aborting does not flush the charge.
        """

        self.warn("aborting controller.")
        if not await self.is_exposing():
           self.warn("Controller is not exposing.")
           return

        CS = ControllerStatus

        await self.set_param(param = "ReadOut", value = int(readout), sync_flag = sync_flag)
        await self.set_param(param = "AbortExposure", value = 1, sync_flag = sync_flag)

        if readout:
            self.update_status([CS.EXPOSING, CS.READOUT_PENDING], "off", notify=False)
            self.update_status(CS.READING)
        else:
            self.update_status([CS.IDLE, CS.READOUT_PENDING])

        return

    async def flush(self, count: int = 2, wait_for: Optional[float] = None,\
                     sync_flag: bool | None = None):
        """Resets and flushes the detector. Blocks until flushing completes."""

        self.notifier("flushing.")

        await self.reset(release_timing=False,sync_flag=False)

        await self.set_param(param = "FlushCount", value = int(count), sync_flag = sync_flag)
        await self.set_param(param = "DoFlush", value = 1, sync_flag = sync_flag)
        await self.send_command(command_string= "RELEASETIMING", sync_flag = sync_flag)

        self.update_status(ControllerStatus.FLUSHING)

        wait_for = wait_for or self.config["timeouts"]["flushing"]
        assert wait_for

        await asyncio.sleep(wait_for * count)

        self.update_status(ControllerStatus.IDLE)

    async def readout(
        self,
        force: bool = False,
        block: bool = True,
        #delay: int = 0,
        wait_for: float | None = None,
        #notifier: Optional[Callable[[str], None]] = None,
        idle_after: bool = True,
        sync_flag: bool | None = None,
    ):
        """Reads the detector into a buffer.

        If ``force``, triggers the readout routine regardless of the detector expected
        state. If ``block``, blocks until the buffer has been fully written. Otherwise
        returns immediately. 

        # not implemented in LS4 timing code
        A ``delay`` can be passed to slow down the readout by as
        many seconds (useful for creating photon transfer frames).
        """

        # NOTE about wbuf:
        # wbuf is determined by the controller, which decided which of its internal memory buffers
        # to hold the next image to be read. 
        # When the Fake_Controller is being used to emulate the real controller, wbuf is initialized
        # to 1 when Fake_Controller is instantiated. Thereafter, it is advanced each time a new image
        # is completely readout (see update_frame)


        #if notifier:
        #  notifier(f"synchronizing...")
        await self.set_param(param="SYNCTEST",value=0, sync_flag = sync_flag)

        #if notifier:
        #  notifier(f"start reading out controller.")

        if (not force) and await self.check_status([ControllerStatus.READOUT_PENDING,ControllerStatus.IDLE],mode='nor'):
            self.error(f"Controller is not in a readable state.")
            raise ArchonControllerError(f"Controller is not in a readable state.")

        await self.reset(autoflush=False, release_timing=False, update_status=False,sync_flag=False)

        await self.set_param(param = "ReadOut", value = 1, sync_flag = sync_flag)

        await self.send_command(command_string = "RELEASETIMING", sync_flag = sync_flag)

        self.timing['readout'].start()
        t=time.time()
        t_start = t
        waited = 0.0
        frame = None

        if self.fake_controller:
           try:
             self.fake_control.update(pixelcount=self.current_window['pixelcount'],\
                                linecount=self.current_window['linecount'])
             # choose next controller buffer ready for writing
             buf = await self.check_buffer(op='write')
             assert buf is not None, "failed to find buffer ready for writing"
             # update the completness for wbuf to False.
             self.fake_control.update_frame(wbuf=buf,complete=False)
             self.fake_control.update_read(t=t,waited=waited)
           except Exception as e:
             error_msg = "Exception starting read of fake controller: %s" % e
             raise ArchonControllerError(error_msg)

        self.update_status(ControllerStatus.READING)

        self.update_status(ControllerStatus.READOUT_PENDING, "off")

        if not block:
           return

        max_wait = self.config["timeouts"]["readout_max"] 

        wait_for = wait_for or 3  # sec delay to ensure the new frame starts filling.

        await asyncio.sleep(wait_for)
        waited = wait_for
        t = time.time()
        if self.fake_controller:
          self.fake_control.update_read(t=t,waited = waited)
          frame= self.fake_control.get_frame()
        else:
          frame = await self.get_frame()

        wbuf=frame['wbuf']
        #self.info("readout out exposure to buffer %d" % wbuf)

        status_interval = 1.0
        update_interval = 0.1

        done = False
        timeout = False
        lines_prev = -1
        t=time.time()
        status_start = t
        dt = 0.0
        while (not done) and (not timeout):

           if waited > max_wait:
              timeout = True
           else:
              if self.fake_controller:
                frame = self.fake_control.get_frame()
              else:
                frame = await self.get_frame()

              if frame[f"buf{wbuf}complete"] == 1:
                 done=True
 
           if not done:
              if dt > status_interval:
                 status_start = time.time()
                 dt = 0.0
                 pixels_read=frame[f"buf{wbuf}pixels"]
                 lines=frame[f"buf{wbuf}lines"]
                 w= int(waited)
                 self.notifier(f"{w}: frame is not complete: {pixels_read} pixel {lines} lines")
                 if lines <= lines_prev:
                    self.error("ERROR reading out at lines = %d, lines_prev = %d, frame: %s" %\
                      (lines, lines_prev,self.print_frame(buf=wbuf,frame=frame)))
                    timeout=True
                 else:
                    lines_prev = lines

              await asyncio.sleep(update_interval)
              t=time.time()
              dt  = t - status_start
              waited = t - t_start
              if self.fake_controller:
                 self.fake_control.update_read(t=t,waited=waited)


        self.timing['readout'].end()
        self.config['expose params']['read-per']=self.timing['readout'].period

        if done:
           self.notifier(f"done reading out controller in %7.3f sec to buffer %d" % \
                (self.timing['readout'].period,wbuf))
           if self.fake_controller:
              self.fake_control.update_read(t=t,waited=waited)
              self.fake_control.update_frame(complete=True)
           if idle_after:
               #notifier(f"idling controller...")
               self.update_status(ControllerStatus.IDLE)
               #notifier(f"done idling controller...")
           # Reset autoflushing.
           await self.set_autoflush(True)

        elif timeout:
           self.error(f"timeout reading out controller")
           self.update_status(ControllerStatus.ERROR)
           self.error("Timed out waiting for controller to finish reading.")
           raise ArchonControllerError(\
                f"Timed out waiting for controller to finish reading.")

        return wbuf

    @overload
    async def fetch(
        self,
        buffer_no: int = -1,
        #notifier: Optional[Callable[[str], None]] = None,
        *,
        return_buffer: Literal[False],
    ) -> numpy.ndarray:
        ...

    @overload
    async def fetch(
        self,
        buffer_no: int = -1,
        #notifier: Optional[Callable[[str], None]] = None,
        *,
        return_buffer: Literal[True],
    ) -> tuple[numpy.ndarray, int]:
        ...

    @overload
    async def fetch(
        self,
        buffer_no: int = -1,
        #notifier: Optional[Callable[[str], None]] = None,
        return_buffer: bool = False,
    ) -> numpy.ndarray:
        ...

    async def fetch(
        self,
        buffer_no: int = -1,
        #notifier: Optional[Callable[[str], None]] = None,
        return_buffer: bool = False,
        sync_flag: bool | None = None,
    ):
        """Fetches a frame buffer and returns a Numpy array.

        Parameters
        ----------
        buffer_no
            The frame buffer number to read. Use ``-1`` to read the most recently
            complete frame.
        return_buffer
            If `True`, returns the buffer number returned.

        Returns
        -------
        data
            If ``return_buffer=False``, returns the fetched data as a Numpy array.
            If ``return_buffer=True`` returns a tuple with the Numpy array and
            the buffer number.

        """


        assert not await self.is_fetching(),"Controller is already fetching"
        assert buffer_no in self.buf_indices + [-1],\
            "Invalid frame buffer: %d" % buffer_no

        frame_info=None
        if self.fake_controller:
          frame_info=self.fake_control.get_frame()
        else:
          frame_info = await self.get_frame()

        #If buffer_no = -1, get oldest completed buffer
        if buffer_no == -1:
            #self.info("getting latest complete buffer")
            buffer_no = await self.check_buffer(frame_info=frame_info,op='fetch')
            if buffer_no is None:
               error_msg ="failed to find buffer ready for fetching"
               self.error(error_msg)
               self.print_frame(frame=frame_info)
               raise ArchonControllerError(error_msg)
        #Otherwise, make sure the specified buffer is complete
        else:
            if frame_info[f"buf{buffer_no}complete"] == 0:
               raise ArchonControllerError(f"Buffer frame {buffer_no} is not complete")

        self.update_status(ControllerStatus.FETCHING)

        #self.info("fetching data from buffer %d" % buffer_no)
        self.timing['fetch'].start()

        # Lock for reading
        await self.send_command(command_string = f"LOCK{buffer_no}",sync_flag=False)

        width = frame_info[f"buf{buffer_no}width"]
        height = frame_info[f"buf{buffer_no}height"]
        bytes_per_pixel = 2 if frame_info[f"buf{buffer_no}sample"] == 0 else 4
        n_bytes = width * height * bytes_per_pixel
        n_blocks: int = int(numpy.ceil(n_bytes / 1024.0))

        start_address = frame_info[f"buf{buffer_no}base"]

        # Set the expected length of binary buffer to read, including the prefixes.
        self.set_binary_reply_size((1024 + 4) * n_blocks)

        cmd_string = f"FETCH{start_address:08X}{n_blocks:08X}"
        #self.notifier ("sending command [%s] with timout=None and sync_flag=False" % cmd_string)
        #cmd: ArchonCommand = await self.send_command(
        #   f"FETCH{start_address:08X}{n_blocks:08X}",
        #   timeout=None,sync_flag=False
        #
        cmd: ArchonCommand = await self.send_command(
            command_string = cmd_string, timeout=None,sync_flag=False)
        
        #self.notifier ("done sending command [%s] with timout=None and sync_flag=False" % cmd_string)

        # Unlock all
        await self.send_command(command_string = "LOCK0",sync_flag=False)

        # The full read buffer probably contains some extra bytes to complete the 1024
        # reply. We get only the bytes we know are part of the buffer.

        if self.fake_controller:
           fetch_time = self.fake_control.conf['fetch_time']
           await asyncio.sleep(fetch_time)
           frame = cast(bytes, self.fake_control.buffers[buffer_no-1][0:n_bytes])
        else:
           frame = cast(bytes, cmd.replies[0].reply[0:n_bytes])

        #frame = cast(bytes, cmd.replies[0].reply[0:n_bytes])

        # Convert to uint16 array and reshape.
        dtype = f"<u{bytes_per_pixel}"  # Buffer is little-endian

        #self.debug("reshaping 1-D array of length %d bytes to 2-D array of height,width = %d,%d and dtype %s" %\
        #        (len(frame),height,width,dtype))
        arr = numpy.frombuffer(frame, dtype=dtype)
        arr = arr.reshape(height, width)


        # Turn off FETCHING bit
        #self.update_status(ControllerStatus.IDLE)
        self.update_status(ControllerStatus.FETCHING, mode = 'off')

        self.timing['fetch'].end()

        self.notifier("time to fetch data from buffer %d : %7.3f sec" % (buffer_no,self.timing['fetch'].period))
 
        # Mark the buffer as fetched by setting completeness to False (i.e. empty)     
        if self.fake_controller:
          #self.info("setting current buffer (%d) to empty" % buffer_no)
          self.fake_control.update_frame(buf_index=buffer_no,complete = False)

        if return_buffer:
            return (arr, buffer_no)

        return arr

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
          if self.fake_controller:
            frame_info=self.fake_control.get_frame()
          else:
            frame_info = await self.get_frame()

        try:
          buffer_no = self.choose_buffer(frame_info=frame_info, complete=complete, latest=latest)
        except Exception as e:
          self.error("Exception checking for buffer ready for op = %s: %s" % (op,e))
  
        return buffer_no

    def set_binary_reply_size(self, size: int):
        """Sets the size of the binary buffers."""

        self._binary_reply = bytearray(size)

    async def _listen(self):
        """Listens to the reader stream and callbacks on message received."""

        if not self._client:  # pragma: no cover
            raise RuntimeError("Connection is not open.")

        assert self._client and self._client.reader

        n_binary = 0
        while True:
            # Max length of a reply is 1024 bytes for the message preceded by <xx:
            # We read the first four characters (the maximum length of a complete
            # message: ?xx\n or <xx\n). If the message ends in a newline, we are done;
            # if the message ends with ":", it means what follows are 1024 binary
            # characters without a newline; otherwise, read until the newline which
            # marks the end of this message. In binary, if the response is < 1024
            # bytes, the remaining bytes are filled with NULL (0x00).
            try:
                line = await self._client.reader.readexactly(4)
            except asyncio.IncompleteReadError:
                return

            if line[-1] == ord(b"\n"):
                pass
            elif line[-1] == ord(b":"):
                line += await self._client.reader.readexactly(1024)
                # If we know the length of the binary reply to expect, we set that
                # slice of the bytearray and continue. We wait until all the buffer
                # has been read before sending the notification. This is significantly
                # more efficient because we don't create an ArchonCommandReply for each
                # chunk of the binary reply. It is, however, necessary to know the
                # exact size of the reply because there is nothing that we can parse
                # to know a reply is the last one. Also, we don't want to keep appending
                # to a bytes string. We need to allocate all the memory first with
                # a bytearray or it's very inefficient.
                #
                # NOTE: this assumes that once the binary reply begins, no other
                # reply is going to arrive in the middle of it. I think that's unlikely,
                # and probably prevented by the controller, but it's worth keeping in
                # mind.
                #
                if self._binary_reply:
                    self._binary_reply[n_binary : n_binary + 1028] = line
                    n_binary += 1028  # How many bytes of the binary reply have we read.
                    if n_binary == len(self._binary_reply):
                        # This was the last chunk. Set line to the full reply and
                        # reset the binary reply and counter.
                        line = self._binary_reply
                        self._binary_reply = None
                        n_binary = 0
                    else:
                        # Skip notifying because the binary reply is still incomplete.
                        continue
            else:
                line += await self._client.reader.readuntil(b"\n")

            self.notify(line)

    
    async def __track_commands(self):
        """Removes complete commands from the list of running commands."""

        while True:
            done_cids = []
            for cid in self.__running_commands.keys():
                if self.__running_commands[cid].done():
                    self._id_pool.add(cid)
                    done_cids.append(cid)
            for cid in done_cids:
                self.__running_commands.pop(cid)
            await asyncio.sleep(0.5)


    def _get_id(self) -> int:
        """Returns an identifier from the pool."""

        if len(self._id_pool) == 0:
            self._reset_id_pool()

        return self._id_pool.pop()


    def _reset_id_pool(self):
        """Reset the identifier pool """

        self._id_pool = set(range(MAX_COMMAND_ID))

    async def erase(self):
        """Run the LBNL erase procedure."""
 
        self.notifier("erasing.")

        await self.reset(release_timing=False, autoflush=False,sync_flag=False)

        self.update_status(ControllerStatus.FLUSHING)

        """
        await self.set_param("DoErase", 1)
        await self.send_command("RELEASETIMING")
        """
        await asyncio.sleep(2)  # Real time should be ~0.6 seconds.

        self.update_status(ControllerStatus.IDLE)

    async def cleanup(
        self,
        erase: bool = False,
        n_cycles: int = 10,
        fast: bool = False,
        sync_flag: bool | None = None,
        #notifier: Callable[[str], None] | None = None,
    ):
        """Runs a cleanup procedure for the LBNL chip.

        Executes a number of cycles of the e-purge routine followed by a chip
        flush (complete or fast). After the e-purge cycles have been completed,
        runs three full flushing cycles.

        Parameters
        ----------
        erase
            Calls the `.erase` routine before running the e-purge cycle.
        n_cycles
            Number of e-purge/flushing cycles to execute.
        fast
            If `False`, a complete flushing is executed after each e-purge (each
            line is shifted and read). If `True`, a binning factor of 10 is used.
        #notifier
        #    A function to call to output messages (usually a command write method).

        """

        #if notifier is None:
        #    notifier = lambda text: None  # noqa

        if erase:
            #notifier("Erasing chip.")
            await self.erase()

        mode = "fast" if fast else "normal"
        purge_msg = f"Doing {n_cycles} with DoPurge=1 (mode={mode})"
        self.notifier(purge_msg)

        for ii in range(n_cycles):
            #notifier(f"Cycle {ii+1} of {n_cycles}.")
            await self.purge(fast=fast)

        await self.set_param(param = "DoPurge", value = 0, sync_flag = sync_flag)

        #flush_msg = "Flushing 3x"
        #self.notifier(flush_msg)

        await self.flush(3)

        await self.reset(sync_flag=False)

        return True

    async def purge(self, fast: bool = True, sync_flag: bool | None = None):
        """Runs a single cycle of the e-purge routine.

        A cycle consists of an execution of the e-purge routine followed by a
        chip flushing.

        Parameters
        ----------
        fast
            If `False`, a complete flushing is executed after the e-purge (each
            line is shifted and read). If `True`, a binning factor of 10 is used.

        """

        self.notifier("Running e-purge.")

        if fast:
            await self.set_param(param = "FLUSHBIN", value = 10,\
                   sync_flag = sync_flag)
            await self.set_param(param = "SKIPLINEBINVSHIFT", value = 220, \
                   sync_flag = sync_flag)
        else:
            await self.set_param(param = "FLUSHBIN", value = 2200, 
                   sync_flag = sync_flag)
            await self.set_param(param = "SKIPLINEBINVSHIFT", value = 1, 
                  sync_flag = sync_flag)

        await self.reset(release_timing=False,sync_flag=False)

        self.update_status(ControllerStatus.FLUSHING)

        await self.set_param(param = "DOPURGE", value = 1, 
                  sync_flag = sync_flag)
        await self.send_command(command_string= "RELEASETIMING")

        flush_time = self.config["timeouts"]["flushing"]
        if fast:
            flush_time = self.config["timeouts"]["fast_flushing"]
        await asyncio.sleep(self.config["timeouts"]["purge"] + flush_time)

        await self.set_param(param = "FLUSHBIN", value = 2200, 
               sync_flag = sync_flag)
        await self.set_param(param = "SKIPLINEBINVSHIFT", value = 1, 
               sync_flag = sync_flag)

        await self.reset(sync_flag=False)

        return True

if "__name__" == "__main__":

    print("hello")
