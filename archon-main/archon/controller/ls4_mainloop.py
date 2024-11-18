# ls4_mainloop.py
#
# define class to set procedure performed by the main loop of the timing
# code when it is idle.

import asyncio
from typing import Any, Callable, Iterable, Literal, Optional, cast, overload

from archon.controller.ls4_logger import LS4_Logger
from archon.controller.maskbits import ControllerStatus as CS

class Mainloop_Function():
  NONE_FUNCTION = 'None'
  CLEAR_FUNCTION = 'clear'
  FLUSH_FUNCTION = 'flush'
  auto_functions = [NONE_FUNCTION,CLEAR_FUNCTION,FLUSH_FUNCTION]
  status_bits = [ CS.NOSTATUS, CS.AUTOCLEAR, CS.AUTOFLUSH]


class LS4_Mainloop():

   
    # auto_functions are the possible functions performed by the controller timing
    # code on each pass through its main loop. 

    
    def __init__( self, ls4_controller = None, ls4_logger: LS4_Logger | None = None, \
                   default_function = None, sample: bool | None = None):

        assert ls4_controller is not None, "ls4_controller is not instantiated"

        self.ls4_controller = ls4_controller
        self.set_param = self.ls4_controller.set_param
        self.update_status = self.ls4_controller.update_status

        if ls4_logger is None:
           self.ls4_logger = LS4_Logger('LS4_CCP')
        else:
           self.ls4_logger=ls4_logger

        self.info = self.ls4_logger.info
        self.debug = self.ls4_logger.debug
        self.warn= self.ls4_logger.warn
        self.error= self.ls4_logger.error
        self.critical= self.ls4_logger.critical

        ML = Mainloop_Function
        if default_function is not None:
           assert default_function in ML.auto_functions,"unrecognized default function: %s" % str(default_function)
           self.default_function=default_function
        else:
           self.default_function = ML.NONE_FUNCTION

        if sample is not None:
           self.default_sample = sample
        else:
           if self.default_function == ML.CLEAR_FUNCTION:
             self.default_sample = False
           else:
             self.default_sample = True 

        #update to latest set value once set.
        self.auto_function = None

    async def restore(self,sample=None):
        """ restore the mainloop function to the initialized function """

        if sample in [True,False]:
           sampling = sample
        else:
           sampling = self.default_sample
              
        self.debug("restoring default mainloop function to %s and sample to %s" %\
                (str(self.default_function),str(sampling)))

        await self.set_auto_function(auto_function = self.default_function, sample=sampling)

    async def set_auto_function(self,auto_function = None, sample=None):
        """ set the mainloop function to the specified function. If sample is specified.
            set the Sample parameter accordingly.
        """

        ML = Mainloop_Function
        error_msg = None

        if auto_function not in ML.auto_functions:
           error_msg = "unrecognized main-loop function: %s" % auto_function

        if error_msg is None:
          if sample in [True,False]:
            sampling = sample
          elif auto_function == ML.CLEAR_FUNCTION:
            sampling = False
          else:
            sampling = True
   
          try:
            if auto_function == ML.NONE_FUNCTION:
              autoflush = False
              autoclear = False
            elif auto_function == ML.FLUSH_FUNCTION:
              autoclear = False
              autoflush = True
            else:
              autoclear = True
              autoflush = False

            self.debug("setting Sampling to %d" % int(sampling))
            await self.set_param("Sampling", int(sampling))
            self.debug("setting autoflush: %s" % autoflush)
            await self.set_param("AutoFlush", int(autoflush))
            self.debug("setting autoclear: %s" % autoclear)
            await self.set_param("AutoClear", int(autoclear))
            self.auto_function = auto_function

            if autoflush:
              self.debug("setting AUTOFLUSH status bit")
              self.update_status (CS.AUTOFLUSH,'on')
            else:
              self.debug("clearing AUTOFLUSH status bit")
              self.update_status (CS.AUTOFLUSH,'off')

            if autoclear:
              self.debug("setting AUTOCLEAR status bit")
              self.update_status (CS.AUTOCLEAR,'on')
            else:
              self.debug("clearing AUTOCLEAR status bit")
              self.update_status (CS.AUTOCLEAR,'off')

          except Exception as e:
            error_msg = "exception setting auto_function and sample to %s %s: %s" %\
              (auto_function,sample,e)

        if error_msg is not None:
           self.error(error_msg)

        return error_msg
