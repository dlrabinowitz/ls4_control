# ls4_exp_modes.py
# Exposure modes  recognized by LS4_CCP
#
#  exp_mode_single : acquire and fetch the same image in sequence
#  exp_mode_first  : acquire a new image but do not fetch
#  exp_mode_next   : fetch previous image while acquiring the next
#  exp_mode_last   : fetch previous image, acquire and fetch a new one

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


