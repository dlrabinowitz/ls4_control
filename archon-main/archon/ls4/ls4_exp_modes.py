############################
# -*- coding: utf-8 -*-
#
# @Author: David Rabinowitz (david.rabinowitz@yale.edu)
# @Date: 2025-06-25
# @Filename: ls4_exp_modes.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)
#
# This file defines  a list  of eposure modes (ls4_exp_modes) recognized by LS4_CCP
# and the respecitve values of parameters "acquire","fetch", and "wait" 
# that determine the actions taken for each each mode.
#
#  exp_mode_single : acquire and fetch the same image in sequence
#  exp_mode_first  : acquire a new image but do not fetch
#  exp_mode_next   : fetch previous image while acquiring the next
#  exp_mode_last   : fetch previous image, acquire and fetch a new one
#
# See expose() and exp_sequence() commands in ls4_control.py
#
############################

exp_mode_single = 'single'
exp_mode_first  = 'first'
exp_mode_next   = 'next'
exp_mode_last   = 'last'
ls4_exp_modes = {\
  exp_mode_first:{'acquire':True,'fetch':False,'wait':True},\
  exp_mode_next:{'acquire':True,'fetch':True,'wait':False},\
  exp_mode_single:{'acquire':True,'fetch':True,'wait':True},\
  exp_mode_last:{'acquire':False,'fetch':True,'wait':True},\
}


