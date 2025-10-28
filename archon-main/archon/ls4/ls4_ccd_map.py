############################
# -*- coding: utf-8 -*-
#
# @Author: David Rabinowitz (david.rabinowitz@yale.edu)
# @Date: 2025-06-25
# @Filename: ls4_ccd_map.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)
#
# Python code defining LS4_CCD_Map class 
# This provides utilities that return positional and instrumental parameters
# for each CCD amplifier based on the instrument wiring , ccd locations, and
# configuration parameters assigned to the controllers.
#
#
# Notes about LS4 tap lines and CCD placement
#
# For each quadrant of the CCD (NW, NE, SW, SE) there are 8 connectors (A, B, ..., H)
# on the mother board, one for each CCD location in the focal plane:
#
#         __________________NORTH__________________
#       |                     |                     |
#       | NW-A NW-B NW-C NW-D | NE-E NE-F NE-G NE-H |
#       |                     |                     |
#       |                     |                     |
#       |                     |                     |
#       | NW-E NW-F NW-G NW-H | NE-A NE-B NE-C NE-D |
#       |                     |                     |
#  WEST | ____________________|_____________________| EAST
#       |                     |                     |
#       |                     |                     |
#       | SW-A SW-B SW-C SW-D | SE-E SE-F SE-G SE-H |
#       |                     |                     |
#       |                     |                     |
#       |                     |                     |
#       | SW-E SW-F SW-G SW-H | SE-A SE-B SE-C SE-D |
#       |                     |                     |
#       | __________________SOUTH___________________|
#
#
# The controller reads out each CCD by two video amplifier outputs or "taps". These
# two outputs read out the "left" and "right" halves of the CCD, respectively.
# and max 8 CCDs. However, the controller can be configured only a subset of the tap.
#
# The taps are numbered 1 to 16, and are assigned a direction for storing the images
# pixels into the frame buffer ("L" or "R"). This preserves the relative pixel orientation
# in the data buffer. The connection in the mother board are assigned taps, as follows:
#
# motherboard controller taps
# location    (left, right)
# A           AD3L,  AD4R
# B           AD2L,  AD1R
# C           AD8L,  AD7R
# D           AD6L,  AD5R
# E           AD12L, AD11R
# F           AD10L, AD9R
# G           AD13L, AD14R
# H           AD15L, AD16R
#
#
# In the controller config file ("*.acf"), the order in which the CCD taps are
# readout into the image buffer is decribed by "TAPLINE0", "TAPLINE1", ...,
# "TAPLINEN", where N is the number of taps that are read out (can be 1 to 16).
# The number of taps read out is specified by "TAPLINES"
# Here is an example:
#  TAPLINE0="AD3L, 1, 4900"
#  TAPLINE1="AD4R, 1, 1000"
#  TAPLINE2="AD12L, 1, 5000"
#  TAPLINE3="AD11R, 1, 700"
#  TAPLINE4=
#  TAPLINES=4
#
#  To provide additional information about CCD locations to the controller, an optional
#  "ccd_map" may be provided. For example, if only location "A" and "E" are occupied :
#
#     ccd_map =  {"A":{"CCD_NAME":"S-003"},
#                 "E":{"CCD_NAME":"S-196"}}
#
#  In this test program, the ccd_map provided in the format of a json-encoded text file:
#  E.G:
#  {"A": {"CCD_NAME": "S-003"}, "E": {"CCD_NAME": "S-196"}}
#
############################

import numpy as np
import sys
import asyncio
import archon
from archon.controller.ls4_logger import LS4_Logger
import json
from . import AMPS_PER_CCD, MAX_CCDS

#

class LS4_CCD_Map():

    # defaults assuming CCDs are read out the both amps
    amps_per_ccd = AMPS_PER_CCD
    max_ccds = MAX_CCDS
    max_taps = amps_per_ccd * max_ccds

    # There are 8 CCD locations per controller ("A",...,"H"). 
    # There are two amps per CCD ("LEFT" and "RIGHT")
    # Each tap name corresponds to one of the amps at one of the CCD locations

    # static map from tap name to ccd and amp location
    tap_locations={"AD3":{"LOCATION":"A","AMP_NAME":"LEFT"}, "AD4":{"LOCATION":"A","AMP_NAME":"RIGHT"},
                   "AD2":{"LOCATION":"B","AMP_NAME":"LEFT"},"AD1":{"LOCATION":"B","AMP_NAME":"RIGHT"},
                   "AD8":{"LOCATION":"C","AMP_NAME":"LEFT"}, "AD7":{"LOCATION":"C","AMP_NAME":"RIGHT"},
                   "AD6":{"LOCATION":"D","AMP_NAME":"LEFT"}, "AD5":{"LOCATION":"D","AMP_NAME":"RIGHT"},
                   "AD12":{"LOCATION":"E","AMP_NAME":"LEFT"}, "AD11":{"LOCATION":"E","AMP_NAME":"RIGHT"},
                   "AD10":{"LOCATION":"F","AMP_NAME":"LEFT"}, "AD9":{"LOCATION":"F","AMP_NAME":"RIGHT"},
                   "AD13":{"LOCATION":"G","AMP_NAME":"LEFT"}, "AD14":{"LOCATION":"G","AMP_NAME":"RIGHT"},
                   "AD15":{"LOCATION":"H","AMP_NAME":"LEFT"}, "AD16":{"LOCATION":"H","AMP_NAME":"RIGHT"}}

    # static map from ccd location to tap names for each amp
    tap_names={"A":{"LEFT":"AD3","RIGHT":"AD4"},
               "B":{"LEFT":"AD2","RIGHT":"AD1"},
               "C":{"LEFT":"AD8","RIGHT":"AD7"},
               "D":{"LEFT":"AD6","RIGHT":"AD5"},
               "E":{"LEFT":"AD12","RIGHT":"AD11"},
               "F":{"LEFT":"AD10","RIGHT":"AD9"},
               "G":{"LEFT":"AD13","RIGHT":"AD14"},
               "H":{"LEFT":"AD15","RIGHT":"AD16"}}

    required_conf_params = ['acf_file','map_file','amp_direction']

    def __init__(self,
        ls4_logger: LS4_Logger | None = None,
        ls4_conf: dict | None = None,
    ):
       
        """ ls4_conf is a dictionary with configuration variables for the instance of LS4_Camera."""
       

        assert ls4_conf is not None,"unspecified ls4 configuration"
        assert ls4_logger is not None,"unspecified ls4_logger"

        self.ls4_conf = ls4_conf
        self.ls4_logger = ls4_logger
        self.info = self.ls4_logger.info
        self.debug= self.ls4_logger.debug
        self.warn = self.ls4_logger.warn
        self.error= self.ls4_logger.error
        self.critical= self.ls4_logger.critical

        # acf_conf is a copy of the archon configuration info initialized by LS4_Controller
        # when the controller is initialized.

        self.acf_conf = None # updated by self.update_ccd_map()

        for param in self.required_conf_params:
            assert param in ls4_conf, \
                    "parameter [%s] must be specified in configuration options [%s]" % (param,ls4_conf)
            assert ls4_conf[param] is not None,\
                    "configuration parameter [%s] can not be None" % param
            assert ls4_conf[param] not in ["","None","NONE","none"], \
                    "configuration parameter [%s] can not be [%s]" % (param,ls4_conf[param])

        assert ls4_conf['amp_direction'] in ["both","left","right"],\
           "config parameters [%s]=[%s] must be both, left, or right" %\
             ('amp_direction',ls4_conf['amp_direction'])

        self.debug("ls4_conf[amp_direction]: %s" % ls4_conf['amp_direction'])

        if ls4_conf['amp_direction'] in ["left","right"] :
          self.amps_per_ccd = int(self.amps_per_ccd/2)
          self.max_taps = self.amps_per_ccd * self.max_ccds
 
        # to be initialized by load_ccd_map()
        self.ccd_map=None

        # filled in by update_ccd_map()
        self.image_info={}

        self.debug("loading ccd map file %s" % ls4_conf['map_file'])
        try: 
           self.load_ccd_map(upper_flag=True)
        except Exception as e:
          raise RuntimeError("unable to load ccd_map: %s" % e)
          return None

    def get_max_ccds(self):
        return self.max_ccds

    def get_max_taps(self):
        return self.max_taps

    def load_ccd_map(self,upper_flag=False):

        """ load contents of json-formatted file(ccd_map_file) in self.ccd_map.
            if upper_flag = True, convert all text in file to upper case before loading.
        """

        ccd_map_file = self.ls4_conf['map_file']
        assert ccd_map_file is not None, "unspecified ccd_map_file"

        try:
          fin = open(ccd_map_file,"r")
        except Exception as e:
          self.error("exception opening ccd_map_file %s: %s" % (ccd_map_file,e))
          raise RuntimerError(e)

        try:
          content = fin.read()
          fin.close()
          if upper_flag:
             content = content.upper()
          self.ccd_map=json.loads(content)
        except Exception as e:
          self.error("exception loading ccd_map from ccd_map_file %s: %s" % (ccd_map_file,e))
          raise RuntimerError(e)

    def update(self,acf_conf=None):

        """ update the ccd data in the ccd_map structure with information from the
            entries in the controller config dictionary (acf_conf). 
            Specifically, associate the taps read out by the controller with the 
            respective CCD names and their locations (A - H) in the array.

            Before ccd_map is updated, it may already specify the name of the CCD for each
            occupied location in the array:

               ccd_map =  ["A":{CCD_NAME":"S-003"},
                           "E":{"CCD_NAME":"S-196"}]

            The config dictionary specifies which taps on the mother-board are being read out
            (there are 2 taps per CCD, one for each amplifier) , the readout order, the 
            orientation of the tap data in the image buffer (left or right ), 
            and the scale and offset applied to the video signal after digitization. 
            Note that all this information is read from an acf config file (see ls4_camera.py)

            For example, here are the entries for an array with 2 CCDs being read out
            through 4 taps:

              TAPLINE0="AD3L, 1, 4900"
              TAPLINE1="AD4R, 1, 1000"
              TAPLINE2="AD12L, 1, 5000"
              TAPLINE3="AD11R, 1, 700"
              TAPLINE4=
              TAPLINES=4

            These entries state there are 4 tap lines being read out in the following order:
             1:  tap index 0 : tap "AD3" with orientation "L", scale 1, and offset 4900
             2:  tap index 1 : tap "AD4" with orientation "R", scale 1, and offset 1000
             3:  tap index 2 : tap "AD12" with orientation "L", scale 1, and offset 5000
             4:  tap index 3 : tap "AD11" with orientation "R", scale 1, and offset 700

            The hard-wired mapping from tap_name to array location is given by the tap_locations
            dictionary 

             A: AD3, AD4
             B: AD2, AD1
             C: AD8, AD7
             D: AD6, AD5
             E: AD12, AD11
             F: AD10, AD9
             G: AD13, AD14
             H: AD15, AD16

            After updating, ccd_map example will be :
               ccd_map =  {"A":{"CCD_NAME":"S-003","TAP_INDICES":[0,1],"TAP_NAMES":["AD3L","AD4R"],
                                "AMP_NAMES":["LEFT","RIGHT"],"TAP_SCALES":[1,1],"TAP_OFFSETS":[4900,1000]},
                           "E":{"CCD_NAME":"S-196","TAP_INDICES":[2,3],"TAP_NAMES":["AD12L","AD11R"},
                                "AMP_NAMES":["LEFT","RIGHT"],"TAP_SCALES":[1,1],"TAP_OFFSETS":[5000,700]} }

            NOTE 1: It is possible for the config_file will be inconsistent with the ccd_map. The 
            config file may list tap names that map to unoccupied array location, or the ccd_map may
            list CCD at locations that are not list in the config file. These conditions will lead to
            raised exceptions.

            NOTE 2: If the ccd_map is uninitialized (i.e. self.ccd_map is None because no ccd_map_file was
            specified at instantiation of LS4_Camera, then this routine will fill in ccd_map 
            assuming there is an unnamed CCD at each location implicitly referenced by the TAPLINE entries
            in acf_conf dictionary. The ccds will be assigned names "GENERIC_CCD-A","GENERIC_CCD-B", etc depending on 
            occupied location.

        """

        # make sure acf_conf includes required keywords

        assert acf_conf, "controller  not instantiated"
        assert "CONFIG" in acf_conf, "CONFIG not in acf_conf"
        assert "PIXELCOUNT" in acf_conf["CONFIG"], "PIXELCOUNT not in acf_conf"
        assert "LINECOUNT" in acf_conf["CONFIG"], "LINECOUNT not in acf_conf"
        assert "FRAMEMODE" in acf_conf["CONFIG"], "FRAMEMODE not in acf_conf"
        assert "TAPLINES" in acf_conf["CONFIG"], "TAPLINES not in acf_conf"


        #self.debug("PIXELCOUNT: %s" % acf_conf["CONFIG"]["PIXELCOUNT"])
        #self.debug("LINECOUNT: %s" % acf_conf["CONFIG"]["LINECOUNT"])

        self.acf_conf = acf_conf

        # make sure the TAPLINES value is in range 1 to 16
        num_taps = int(acf_conf["CONFIG"]["TAPLINES"])
        assert num_taps >0 and num_taps<=self.max_taps,\
                "num_taps [%d] is out of range 0 to %d" % (num_taps,self.max_taps)

        # make sure the number of taps is an integer multiple of amps_per_ccd
        assert self.amps_per_ccd * (num_taps // self.amps_per_ccd) == num_taps,\
                "number of taps [%d] is not a multiple of amps_per_ccd [%d]" % (num_taps, self.amps_per_ccd)

        # make sure there is a "TAPLINEx" entry in acf_conf for each tap_index from 0 to num_taps-1.
        # Also make sure there are three values specified for each tap_index (tap_name,scale,offset).
        # save these data in tap_info.

        tap_info=[]
        for tap_index in range(0,num_taps):
          key="TAPLINE%d" % tap_index
          assert key in acf_conf["CONFIG"], "key %s not in acf_conf" % key
          data = acf_conf["CONFIG"][key].replace('"','')
          data = data.split(",")
          assert len(data) == 3, "unexpected data for key %s: %s" % (key,data)
          #put the data into a dictionary format
          info= {"TAP_NAME":data[0].upper(),\
                 "TAP_INDEX":tap_index,\
                  "TAP_SCALE":int(data[1]),\
                  "TAP_OFFSET":int(data[2])}
          tap_info.append(info)

        # record relevant config info in self.image_info
        self.image_info['num_pixels'] = int(acf_conf["CONFIG"]["PIXELCOUNT"])
        self.image_info['num_lines'] = int(acf_conf["CONFIG"]["LINECOUNT"])
        self.image_info['frame_mode'] = int(acf_conf["CONFIG"]["FRAMEMODE"])
        self.image_info['num_taps'] = num_taps
        self.image_info['amps_per_ccd'] = self.amps_per_ccd

        # create tap_data list to store information for each tap index
        # Each entry will have the following format:
        # {"LOCATION":location,"AMP_NAME":amp_name,"TAP_NAME":tap_name,"TAP_INDEX":tap_index,"TAP_SCALE":tap_scale,"TAP_OFFSET":tap_offset}

        tap_data = []
        for tap_index in range(0,num_taps):

          # get info for this tap index
          info=tap_info[tap_index]

          # get the location info  for this tap .
          # location info is, for example: {"LOCATION":"B","AMP_NAME":"LEFT"}
          location_info =  self._get_tap_location_info(info["TAP_NAME"])

          # add the location info to the tap_data for this tap_index
          info.update(location_info)

          tap_data.append(info)


        # if ccd_map is not initialized, fill it with dummy CCD names, one at
        # each location referenced by tap_data
        if self.ccd_map is None:
          self.ccd_map={}
          for tap_info in tap_data:
             location=tap_info["LOCATION"]
             if location not in self.ccd_map:
                ccd_name = "GENERIC_CCD-"+location
                self.ccd_map[location]={"CCD_LOC":ccd_name}

        # Make sure each ccd location in ccd_map has 1 or 2 entries in tap_data
        # (one for each amp that may be read out).
        
        for location in self.ccd_map:
           num_matched=0
           for entry in tap_data:
               if entry["LOCATION"] == location:
                  num_matched += 1
           assert num_matched > 0, \
              "occupied ccd location %s does not appear in tap data of acf file" % location
           assert num_matched < 3, \
              "occupied ccd location %s appears more than twice in tap data of acf file" % location

        # Make sure each tap index in tap_data has a location with a  matching an entry in ccd_map.

        for tap_info in tap_data:
           location=tap_info["LOCATION"]
           assert location in self.ccd_map, \
                "ccd location %s is read out (tap_index %d) but does not appear in tap_map" % \
                 (location,tap_index)

        # add the info in each tap_data entry to the respective entries in ccd_map.
        # key_map gives the correspondences between the entry keys.
        key_map={"AMP_NAME":"AMP_NAMES","TAP_NAME":"TAP_NAMES",\
                "TAP_INDEX":"TAP_INDICES","TAP_SCALE":"TAP_SCALES",\
                "TAP_OFFSET":"TAP_OFFSETS"}

        for t_info in tap_data:
            location = t_info["LOCATION"]
            ccd_info = self.ccd_map[location]
            #print("ccd_info: %s" % ccd_info)
            for tap_key in key_map:
                ccd_key =key_map[tap_key]
                if tap_key in t_info:
                   data = t_info[tap_key]
                   if ccd_key not in ccd_info:
                      ccd_info[ccd_key]=[]
                   ccd_info[ccd_key].append(data)
 
        self.image_info['num_ccds'] = len(self.ccd_map)

    def get_image_info(self):
        return self.image_info

    def get_amp_selection (self,amp_index):

        """ Return LEFT, RIGHT, ... depending on value of amp_index """

        if  amp_index not in range(0,self.amps_per_ccd):
            self.warn("amp_index [%d] out of range [0 to %d]" % (amp_index, self.amps_per_ccd))
            return None

        if self.ls4_conf['amp_direction'] == 'left':
           return "LEFT"
        elif self.ls4_conf['amp_direction'] == 'right':
           return "RIGHT"
        elif amp_index == 0:
           return "LEFT"
        elif amp_index == 1:
           return "RIGHT"
        else:
           return None

    def _get_tap_location_info(self,tap_name=""):

        """ given tap name, return tap location info """

        name = tap_name.upper()
        name = name.replace("L","").replace("R","")
        assert name in self.tap_locations, "invalid tap name %s" % tap_name
        return self.tap_locations[name]

    def _get_ccd_location(self,ccd_name=None,tap_name=None):

        """ given ccd_name or tap_name, return ccd location"""

        assert ccd_name is not None or tap_name is not None,\
            "neither ccd_name or tap_name is specified"

        ccd_location = None

        if ccd_name is not None:
          ccd_name = ccd_name.upper()
          for location, ccd_info in self.ccd_map:
             if ccd_info["CCD_LOC"] == ccd_name:
               ccd_location = location

        elif tap_name is not None:
           try:
             location_info=self._get_tap_location_info(tap_name)
           except Exception as e:
             self.error("failed to get location for tap %s: %s" % (tap_name,e))

        assert ccd_location is not None,\
           "failed to get ccd_location for ccd_name %s and tap_name %s" %\
                (ccd_name,tap_name)

        return ccd_location


    def _get_tap_data(self,ccd_name=None,ccd_location=None,amp_name=None,data_key=None):

        """ given ccd name or location, return data specified by data_key.
            if amp_name is "BOTH" or None, return the data for both amps.
            If amp is "LEFT" or "RIGHT", return only the data for the specified amp.

            The data are returned as a list
        """

        assert data_key in ["AMP_NAMES","TAP_NAMES","TAP_INDICES","TAP_SCALES""TAP_OFFSETS"],\
                "invalid data_key: %s" % data_key

        assert ccd_name is not None or ccd_location is not None,\
                "both ccd_name and ccd_location are unspecified"

        assert (amp_name is None) or (amp_name in ["LEFT","RIGHT","BOTH"]),\
               "amp_name %s must be LEFT,RIGHT,BOTH, or None" % amp_name

        
        info = None
        # retrieve the info from ccd_map for the specified ccd location
        if ccd_location is not None:
           location = ccd_location.upper()
           assert location in self.ccd_map, "ccd location %s is not in ccd_map" % location
           info = self.ccd_map[location]

        # or else retrieve the info from ccd_map for the specified ccd name
        else:
           name = ccd_name.upper()
           for entry in self.ccd_map:
               if "CCD_LOC" in entry and name  == entry["CCD_LOC"]:
                   info = entry
           
        assert info is not None, "no ccd info found for ccd name %s or location %s" %\
                    (ccd_name,ccd_location)

        key = data_key.upper()
        assert key in info, "no data_key named %s found for ccd name %s or location %s" %\
                    (data_key,ccd_name,ccd_location)

        data = info[key]
        if amp_name in ['LEFT','RIGHT']:
          assert len(data) >= 1, "expected one entries for %s, but found %d" % (key,len(data))
        else:
          assert len(data) == 2, "expected two entries for %s, but found %d" % (key,len(data))
          

        if amp_name is None or  amp_name.upper() == "BOTH":
           return data
        elif amp_name.upper() == "LEFT":
           return [data[0]]
        else:
           return [data[1]]


    def get_tap_indices(self,ccd_name=None,ccd_location=None, amp_name=None):

        """ given ccd name or location, return tap indices"""

        return self._get_tap_data(ccd_name=ccd_name,ccd_location=ccd_location,\
                amp_name=amp_name,data_key="TAP_INDICES")
