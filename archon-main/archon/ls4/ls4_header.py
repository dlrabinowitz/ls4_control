############################
# -*- coding: utf-8 -*-
#
# @Author: David Rabinowitz (david.rabinowitz@yale.edu)
# @Date: 2024-01-16
# @Filename: ls4_header.py 
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)
#
# Python code defining LS4_Header class , with code to manager initialize, update,
# and manager header info for fits file.
#
################################

import archon
import threading
import asyncio
from archon.controller.ls4_logger import LS4_Logger
from archon.ls4.ls4_ccd_map import LS4_CCD_Map

class MyLock():

    def __init__(self,ls4_logger=None,name=None):
           
        self.ls4_logger = ls4_logger

        if name is None:
          self.name = "un-named"
        else:
          self.name = name

        self.info = self.ls4_logger.info
        self.debug= self.ls4_logger.debug
        self.warn = self.ls4_logger.warn
        self.error= self.ls4_logger.error
        self.critical= self.ls4_logger.critical
           
        self.async_lock = asyncio.Lock()

    def release(self):
        self.debug("%s: releasing..." % self.name)
        self.async_lock.release()
        self.debug("%s: done releasing..." % self.name)

    async def acquire(self):
        self.debug("%s: acquiring ..." % self.name)
        await self.async_lock.acquire()
        self.debug("%s: done acquiring" % self.name)

class LS4_Header():

       
    def __init__(self,
        ls4_logger: LS4_Logger | None = None,
        name = None
    ):
       
        self.ls4_logger = ls4_logger
        if name is not None:
           self.name = name
        else:
           self.name = "un-named"

        self.info = self.ls4_logger.info
        self.debug= self.ls4_logger.debug
        self.warn = self.ls4_logger.warn
        self.error= self.ls4_logger.error
        self.critical= self.ls4_logger.critical

        self.header_info={}

        #self.lock = asyncio.Lock()
        self.lock = MyLock(ls4_logger=self.ls4_logger,name = self.name)
 
    async def initialize(self,conf=None):
        error_msg = None

        self.debug("%s: initializing ..." % self.name)

        await self.lock.acquire()
        self.header_info={}
        self.lock.release()

        if conf is not None:
           try:
             await self.set_header_info(conf=conf)
           except Exception as e:
             error_msg = "exception initializeing header: %s" %e

        if error_msg:
           raise RuntimeError(error_msg)

        self.debug("%s: done initializing" % self.name)

    @property 
    async def header(self):
        return await self.get_header()

    async def get_header(self):
        self.debug("%s: getting header ..." % self.name)
        await self.lock.acquire()
        h={}
        h.update(self.header_info)
        self.lock.release()
        self.debug("%s: done getting header " % self.name)
        return h

    #async def _update_header(self,header=None,conf=None,reject_keys=None):
    async def _update_header(self,conf=None,reject_keys=None):

        #""" update header (or self.header_info if header = None) with key,value pairs 
        #    in given configuration dictionary.
        #    Ignore keys specified by reject_keys.
        #"""
        """ update self.header_info with key,value pairs in conf.
            Ignore keys specified by reject_keys.
        """

        self.debug("%s: updating header ..." % self.name)

        #if header is None:
        #  update_flag = True 
        #  header = await self.get_header()
        #else:
        #  update_flag = False
        header={}
        header.update(self.header_info)

        if reject_keys is None:
           reject_keys={}

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

        self.header_info.update(header)
        self.debug("%s: done updating header " % self.name)

    async def set_header_info(self,conf=None,ls4_ccd_map=None,ccd_location=None,amp_index=None):

        """
            Add entries to fits header data in self.header_info.
            If conf is specified, use only the entries from conf.

            If ls4_ccd_map, ccd_location, and amp_index are specifed, then add
            the corresponding ccd info from  ls4_ccd_map.

            If conf is specified, ls4_ccd_map, and ccd_location are ignored.
            if ls4_ccd_map,ccd_location,and amp_index are specified, conf is ignore.

            Return with newly updated header
        """

        #  example ccd_map:
        #      ccd_map =  {"A":{"CCD_NAME":"S-003","TAP_INDICES":[0,1],"TAP_NAMES":["AD3L","AD4R"],
        #                       "AMP_NAMES":["LEFT","RIGHT"],"TAP_SCALES":[1,1],"TAP_OFFSETS":[4900,1000]},
        #                  "E":{"CCD_NAME":"S-196","TAP_INDICES":[2,3],"TAP_NAMES":["AD12L","AD11R"},
        #                       "AMP_NAMES":["LEFT","RIGHT"],"TAP_SCALES":[1,1],"TAP_OFFSETS":[5000,700]} }


        try:
          assert (conf is not None) or\
            ((ls4_ccd_map is not None) and (ccd_location is not None) and (amp_index is not None)), \
              "must specify conf or else ls4_ccd_map, ccd_location, and amp_index"
        except Exception as e:
          self.error(e)
          return  None

        self.debug("%s: setting header info ... " % self.name)

        h = {}

        if conf is not None:
          reject_keys=[]
          for key in conf:
             #if "_list" in key or 'log_format' in key or 'frame' in key:
             if "_list" in key or 'log_format' in key:
                reject_keys.append(key)
             elif isinstance(conf[key],(dict)):
                h.update(conf[key])
             elif isinstance(conf[key],(list,tuple)):
                pass
             else:
                h[key]=conf[key]

        else:

          try:
            assert amp_index is not None, "unspecified amp index"
            assert ccd_location in ls4_ccd_map.ccd_map, "ccd location %s not found in ccd map" % ccd_location
            assert amp_index in range(0,ls4_ccd_map.amps_per_ccd),\
                    "amp_index [%d] out of range [0 to %d]" % (amp_index,ls4_ccd_map.amps_per_ccd)
          except Exception as e:
            self.error(e)
            return 

          # map to translate keyword in  ccd_info dictionary to keyword in header
          key_map={"AMP_NAME":"AMP_NAMES","TAP_NAME":"TAP_NAMES",\
                  "TAP_INDEX":"TAP_INDICES","TAP_SCALE":"TAP_SCALES",\
                  "TAP_OFFSET":"TAP_OFFSETS"}

          ccd_info = ls4_ccd_map.ccd_map[ccd_location]
          h.update({"CCD_LOC":ccd_info["CCD_LOC"],"CCD_NAME":ccd_info["CCD_NAME"]})

          for key in key_map:
              k = key_map[key]
              value = ccd_info[k][amp_index]
              h.update({key:value})


        await self.lock.acquire()
        await self._update_header(conf=h)
        h = self.header_info
        self.lock.release()

        self.debug("%s: done setting header info " % self.name)
        return h
