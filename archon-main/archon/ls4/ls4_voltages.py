############################
# -*- coding: utf-8 -*-
#
# @Author: David Rabinowitz (david.rabinowitz@yale.edu)
# @Date: 2024-06-25
# @Filename: ls4_voltages.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)
#
# Python code defining LS4_Voltage class .

# This checks camera biases and clock voltages againsts
# programmed values.
#
################################

import numpy as np
import asyncio
from archon.controller.ls4_logger import LS4_Logger
from archon.controller.ls4_controller import LS4Controller
from . import VOLTAGE_TOLERANCE, MAX_FETCH_TIME, AMPS_PER_CCD, MAX_CCDS
from archon.tools import get_obsdate

class LS4_Voltages:
           
    bias_names = [\
          'lvhc_v1',\
          'lvhc_v2',\
          'lvhc_v3',\
          'lvhc_v4',\
          'lvhc_v5',\
          'vhc_v6',\
          'xvn_v1',\
          'xvn_v2',\
          'xvn_v3',\
          'xvn_v4',\
          'xvp_v1',\
          'xvp_v2',\
          'xvp_v3',\
          'xvp_v4',\
    ]

    voltage_names = [\
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

    conf_keys=[\
      'mod4\\lvhc_v1',\
      'mod4\\lvhc_v2',\
      'mod4\\lvhc_v3',\
      'mod4\\lvhc_v4',\
      'mod4\\lvhc_v5',\
      'mod4\\lvhc_v6',\
      'mod9\\xvn_v1',\
      'mod9\\xvn_v2',\
      'mod9\\xvn_v3',\
      'mod9\\xvn_v4',\
      'mod9\\xvp_v1',\
      'mod9\\xvp_v2',\
      'mod9\\xvp_v3',\
      'mod9\\xvp_v4',\
    ]

    supply_voltage_keys=[\
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

    status_keys=[\
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

    conf_enable_keys=[\
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

    def __init__(self,ls4_controller=None,logger=None):

        assert ls4_controller is not None, "ls4_controller is unspecified"

        self.ls4_controller = ls4_controller
        self.fake_controller = self.ls4_controller.fake_controller

        if logger is None:
           self.logger = LS4_Logger()
        else:
           self.logger = logger

        self.info = self.logger.info
        self.debug= self.logger.debug
        self.warn = self.logger.warn
        self.error= self.logger.error
        self.critical= self.logger.critical


    async def check_voltages(self,status=None,voltage_tolerance=VOLTAGE_TOLERANCE,
              bias_name=None, voltage_name=None):
        """ 
            check that bias and supply voltages are within desired tolerance.
            If bias_name is specified, check only this specific bias.
            If voltage_name is specified, check only this specfific voltage.
        """
          


        assert status is not None, "status is not instantiated"
        assert self.ls4_controller is not None, "ls4_controller is not instantiated"
        assert (bias_name is None) or (voltage_name is None),\
               "can not specifiy both a bias and a supply voltage name"

        if bias_name is not None:
           assert bias_name in self.bias_names,\
           "unrecognized bias name: %s" % bias_name
        elif voltage_name is not None:
           assert voltage_name in  self.voltage_names,\
           "unrecognized voltage name: %s" % voltage_name

        in_tolerance = None
        v_set = None
        v_meas = None
        enabled = None

        # check biases only if no voltage name is specified
        if voltage_name is None:
          conf = self.ls4_controller.acf_config["CONFIG"]
          index = 0
          for c_key in self.conf_keys:
            if bias_name is None or bias_name in c_key:
              if in_tolerance is None:
                 in_tolerance = True
              s_key = self.status_keys[index]
              c_enable_key = self.conf_enable_keys[index]
              name = self.bias_names[index]
              assert c_key in conf, "config key %s not found in conf" % c_key
              assert c_enable_key in conf, "config key %s not found in conf" % c_enable_key
              assert s_key in status, "status key %s not found in status" % s_key
              if conf[c_enable_key] in [1,"1"]:
                 enabled=True
              else:
                 enabled=False
              v_set = float(conf[c_key])
              if self.fake_controller:
                if enabled:
                  v_meas = v_set
                else:
                  v_meas = 0.0
              else:
                v_meas = status[s_key]
              if enabled:
                if  np.fabs(v_set-v_meas) > max(voltage_tolerance,0.01*np.fabs(v_set)):
                   self.warn("bias %s is out of tolerance: set: %7.3f actual: %7.3f" % (c_key,v_set,v_meas))
                   in_tolerance = False
                else:
                   self.debug("bias %s is in range: set: %7.3f actual: %7.3f" % (c_key,v_set,v_meas))
              else:
                self.debug("bias %s is disabled: set: %7.3f actual: %7.3f" % (c_key,v_set,v_meas))
            index += 1

        # check supply voltages only if no bias name is specified
        elif bias_name is None:
          assert "supply voltages" in self.ls4_controller.config, "no supply voltages in config"
          conf = self.ls4_controller.config["supply voltages"]
          self.debug("conf = %s" % str(conf))
          for supply_key in self.supply_voltage_keys:
            if voltage_name is None or voltage_name in supply_key:
              if in_tolerance is None:
                 in_tolerance = True
              assert supply_key in conf, "supply_voltage key %s not found in conf" % supply_key
              assert supply_key in status, "supply_voltage key %s not found in status" % supply_key
              v_set = float(conf[supply_key])
              v_meas = status[supply_key]

              ## +/-100v power supply voltages (now actually set to  +/-50v) are normally off by 0.95 
              if supply_key in ["n100v_v","p100v_v"]:
                v_set =0.95*v_set
                v_tol = 2.0
              else:
                v_tol = voltage_tolerance

              if self.fake_controller:
                 v_meas = v_set

              v_tol =  max(v_tol,0.01*np.fabs(v_set))

              if np.fabs(v_set-v_meas) > v_tol:
                 self.warn("supply voltage %s is out of tolerance: set: %7.3f measured: %7.3f tol: %7.3f" %\
                         (supply_key,v_set,v_meas,v_tol))
                 in_tolerance = False
              else:
                 self.debug("supply voltage %s is in range: set: %7.3f measured: %7.3f" % (c_key,v_set,v_meas))

        if bias_name is not None:
              assert in_tolerance is not None, "unrecognized bias name: %s" % bias_name
        elif voltage_name is not None:
              assert in_tolerance is not None, "unrecognized voltage name: %s" % voltage_name

        if bias_name is None and voltage_name is None:
          return in_tolerance
        elif bias_name is not None:
          return {'enabled':enabled,'v_set':v_set,'v_meas':v_meas,'ok':in_tolerance}

