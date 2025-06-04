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
from archon.controller.ls4_logger import LS4_Logger
from archon.ls4.ls4_ccd_map import LS4_CCD_Map

class LS4_Header():




    def __init__(self,
        ls4_logger: LS4_Logger | None = None,
        ls4_conf: dict | None = None,
        ls4_ccd_map: LS4_CCD_Map | None = None
    ):
       
        """ ls4_conf is a dictionary with configuration variables for the instance of LS4_Camera.
       
        """


        assert ls4_conf is not None,"unspecified ls4 configuration"
        assert ls4_ccd_map is not None,"unspecified ls4_ccd_map"
        assert ls4_logger is not None,"unspecified ls4_logger"

        self.ls4_logger = ls4_logger

        self.info = self.ls4_logger.info
        self.debug= self.ls4_logger.debug
        self.warn = self.ls4_logger.warn
        self.error= self.ls4_logger.error
        self.critical= self.ls4_logger.critical

        self.ls4_conf = ls4_conf
        self.ls4_ccd_map = ls4_ccd_map

        self.header_info={}
 
    def initialize(self):
        self.header_info={}

    def get_header(self):
        return self.header_info

    def _update_header(self,header=None,conf=None,reject_keys=None):

        """ update header (or self.header_info if header = None) with key,value pairs 
            in given configuration dictionary.
            Ignore keys specified by reject_keys.
        """

        if header is None:
          self_update = True 
          header = self.header_info
        else:
          self_update = False

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
              self.header.update({key:value})
            except Exception as e:
              self.error("Exception updating update header with configuration key,value %s %s: %s" %\
                        (key,dict[key],e))

        if self_update:
           self.header_info.update(header)

    def set_header_info(self,conf=None,ccd_location=None,amp_index=None):

        """
            Add entries to fits header data in self.header_info.
            If conf is specified, use only the entries from conf.

            If ccd_location and amp_index are specifed, then add
            the corresponding ccd info from  self.ls4_ccd_map.

            If conf is specified, ccd_location must be None.
            if ccd_location is specified, conf must be None.

            Return with newly updated header
        """

        #  example ccd_map:
        #      ccd_map =  {"A":{"CCD_NAME":"S-003","TAP_INDICES":[0,1],"TAP_NAMES":["AD3L","AD4R"],
        #                       "AMP_NAMES":["LEFT","RIGHT"],"TAP_SCALES":[1,1],"TAP_OFFSETS":[4900,1000]},
        #                  "E":{"CCD_NAME":"S-196","TAP_INDICES":[2,3],"TAP_NAMES":["AD12L","AD11R"},
        #                       "AMP_NAMES":["LEFT","RIGHT"],"TAP_SCALES":[1,1],"TAP_OFFSETS":[5000,700]} }


        try:
          assert (conf is None) or (ccd_location is None), "can not specificy both conf and ccd_location"  
        except Exception as e:
          self.error(e)
          return 

        if conf is not None:
          reject_keys=[]
          h={}
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

          self._update_header(conf=h,reject_keys=reject_keys)
          header = self.header_info

        elif ccd_location is not None:

          try:
            assert amp_index is not None, "unspecified amp index"
            assert ccd_location in self.ls4_ccd_map.ccd_map, "ccd location %s not found in ccd map" % ccd_location
            assert amp_index in range(0,self.ls4_ccd_map.amps_per_ccd),\
                    "amp_index [%d] out of range [0 to %d]" % (amp_index,self.ls4_ccd_map.amps_per_ccd)
          except Exception as e:
            self.error(e)
            return 

          # map to translate keyword in  ccd_info dictionary to keyword in header
          key_map={"AMP_NAME":"AMP_NAMES","TAP_NAME":"TAP_NAMES",\
                  "TAP_INDEX":"TAP_INDICES","TAP_SCALE":"TAP_SCALES",\
                  "TAP_OFFSET":"TAP_OFFSETS"}

          ccd_info = self.ls4_ccd_map.ccd_map[ccd_location]
          self._update_header(conf={"CCD_LOC":ccd_info["CCD_LOC"]})
          self._update_header(conf={"CCD_NAME":ccd_info["CCD_NAME"]})

          for key in key_map:
              k = key_map[key]
              value = ccd_info[k][amp_index]
              self._update_header(conf={key:value})
 
          header = self.header_info

        else:
          header = self.header_info

        return header
