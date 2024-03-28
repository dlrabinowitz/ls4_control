#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: David Rabinowitz (david.rabinowitz@yale.edu)
# @Date: 2023-12-18
# @Filename: ls4_device.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

# Class to handle LS4 logging

import sys
import os
from archon import log
import logging
from inspect import currentframe, getframeinfo



class LS4_Logger():

    def __init__(
      self,
      leader: bool | None = None,
      name=None,
      info=None,
      debug=None,
      error=None,
      warn=None,
      critical=None
    ):

      if leader is not None:
         print("leader = %s" % leader)
         self.leader=leader
      else:
         self.leader=False

      if name is not None:
         self.name=name
      else:
         self.name="ctrl"

      self.info = self.ls4_info
      self.debug= self.ls4_debug
      self.warn = self.ls4_warn
      self.error = self.ls4_error
      self.critical= self.ls4_critical

      if info is not None:
         self.info = info
      if debug is not None:
         self.debug= debug
      if warn is not None:
         self.warn = warn
      if error is not None:
         self.error = error
      if critical is not None:
         self.critical= critical

    def ls4_info(self,s: str):
      #if self.leader or self.name == "ctrl1":
        cf=currentframe()
        fi=getframeinfo(cf.f_back)
        s1 = "[" + os.path.basename(fi.filename) + ":" +  str(fi.lineno) + "] " + ("%s: " % self.name) + s
        log.info(s1)

    def ls4_error(self,s: str):
        cf=currentframe()
        fi=getframeinfo(cf.f_back)
        s1 = "[" + os.path.basename(fi.filename) + ":" +  str(fi.lineno) + "] " + ("%s: " % self.name) + s
        log.error(s1)
        sys.stdout.flush()
        sys.stderr.flush()

    def ls4_warn(self,s: str):
        cf=currentframe()
        fi=getframeinfo(cf.f_back)
        s1 = "[" + os.path.basename(fi.filename) + ":" +  str(fi.lineno) + "] " + ("%s: " % self.name) + s
        log.warning(s1)
        sys.stdout.flush()
        sys.stderr.flush()

    def ls4_debug(self,s: str):

        cf=currentframe()
        fi=getframeinfo(cf.f_back)
        s1 = "[" + os.path.basename(fi.filename) + ":" +  str(fi.lineno) + "] " + ("%s: " % self.name) + s
        log.debug(s1)
        sys.stdout.flush()
        sys.stderr.flush()

    def ls4_critical(self,s: str):
        cf=currentframe()
        fi=getframeinfo(cf.f_back)
        s1 = "[" + os.path.basename(fi.filename) + ":" +  str(fi.lineno) + "] " + ("%s: " % self.name) + s
        log.critical(s1)
        sys.stdout.flush()
        sys.stderr.flush()

    def set_format(self,log_format: str):

        try:
             logging.basicConfig(format=log_format)
        except Exception as e:
             self.warn("unable to set log format to %s" % log_format)

    def set_level(self,log_level: str):

        log.setLevel(logging.NOTSET)
        if log_level in ["DEBUG","debug","Debug"]:
           log.setLevel(logging.DEBUG)
        elif log_level in ["INFO","info","Info"]:
           log.setLevel(logging.INFO)
        elif log_level in ["WARN","warn","Warn"]:
           log.setLevel(logging.WARNING)
        elif log_level in ["ERROR","error","Error"]:
           log.setLevel(logging.ERROR)
        elif log_level in ["CRITICAL","critical","Critical"]:
           log.setLevel(logging.CRITICAL)


#"""
if( __name__ == '__main__'):

  lg=LS4_Logger(leader=True)
  lg.set_format("%(message)s")

  lg.info("hello info")
  lg.debug("hello debug")
  lg.warn("hello warn")
  lg.error("hello error")
  lg.critical("hello critical")
#"""
