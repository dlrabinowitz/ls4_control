# class LS4_Status handles over-all management of status for LS4_CONTROL
#
#   .update() :  update status with dictionary of status values
#   .status: returns the latest status
#   .clear() : clears the current status

import sys
import os
from archon import log
import logging
import threading

from archon.controller.ls4_logger import LS4_Logger   
from archon.tools import get_obsdate

class LS4_Status():
    """ maintain status dictionary for LS4_CCP class """

    # timeout when waiting for status lock to release
    STATUS_LOCK_TIMEOUT=5

    def __init__(self,logger=None):

        if logger is None:
           self.logger = LS4_Logger()
        self.info = self.logger.info
        self.debug= self.logger.debug
        self.warn = self.logger.warn
        self.error= self.logger.error
        self.critical= self.logger.critical

        self._status={}

        # need a mutex to lock self.status while changing status 
        self.status_lock = threading.Lock()

    @property
    def status(self):
        return self.get()

    def update(self,s=None):
        if s is not None:
           self.set(s)

    def get(self,keyword=None):
        """Returns the status of the controller using thread-locking.
           If keyword is a valid key of self._status, return the value for that keyword
        """

        status = None
        error_msg = None

        error_msg = self.acquire_lock()
        if error_msg is None:
          if (keyword is not None) and (keyword in self._status):
             state = self._status[keyword]
          else:
            state = self._status
        error_msg = self.release_lock()

        if error_msg is not None:
          self.error(error_msg)
          return error_msg
        else:
          return state

    def set(self,s=None):
        """updates the status of the controller with dictionary s using thread-locking """

        error_msg = None

        if s is not None:

            error_msg = self.acquire_lock()
            if error_msg is None:
              dt=get_obsdate()
              self._status.update(s)
              self._status.update({'date':dt})
            error_msg = self.release_lock()

            if error_msg is not None:
              self.error(error_msg)

        return error_msg

    def clear(self):
        """ clear the status """

        error_msg = self.acquire_lock()

        if error_msg is None:
          self._status = {}
        error_msg = self.release_lock()

        if error_msg is not None:
          self.error(error_msg)

        return error_msg


    def acquire_lock(self):
        """ set the status thread lock. Return error_msg (None on success) """

        error_msg = None
        try:
          if not self.status_lock.acquire(timeout=self.STATUS_LOCK_TIMEOUT):
             error_msg = "ERROR: failed to acquire status lock within %7.3f sec" %\
                  self.STATUS_LOCK_TIMEOUT
             self.warn(error_msg)
        except Exception as e:
          error_msg = "Exception acquiring status lock"
          self.warn(error_msg)

        if error_msg:
          self.warn(error_msg)

        return error_msg

    def release_lock(self):
        """ release the status thread lock. Return error_msg (None on success) """

        error_msg = None
        try:
          self.status_lock.release()
        except Exception as e:
          error_msg = "Exception releasing status lock"
          self.warn(error_msg)
        if error_msg:
          self.warn(error_msg)

        return error_msg


    def status_callback(self,keyword=None,value=None):
        """ update the status with the specified keyword and value"""

        if keyword is not None:
           try:
               self.update({keyword:value})
           except Exception as e:
               self.error("unable to update status: keyword %s value %s: %s" %\
                     (keyword,str(value),e))


