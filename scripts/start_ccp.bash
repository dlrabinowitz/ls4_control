#!/bin/bash
source ~/ls4_venv/bin/activate
LOG_LEVEL="DEBUG"
EXPTIME=0.25
INITIAL_CLEAR="False"
IDLE_FUNCTION='clear'
SUB_READOUT="False"
RESET_FLAG="False"
REBOOT_FLAG="False"
POWER_DOWN="False"

if [ $1 == "reset" ] ; then
  RESET_FLAG="True"
fi

if [ $1 == "reboot" ] ; then
  REBOOT_FLAG="True"
fi

if [ $1 == "subread" ]; then
  SUB_READOUT="True"
fi

if [ $1 == "poweroff" ]; then
  RESET_FLAG="True"
  POWER_DOWN="True"
fi

dt=`date +"LS4_%Y%m%d%H%M%S"`
IMG_PREFIX=$dt
CONF_PATH=$LS4_CONTROL_ROOT/conf
SCRIPTS=$LS4_CONTROL_ROOT/scripts
PYTHON=$LS4_CONTROL_ROOT/python 
LPYTHON=$LS4_CONTROL_ROOT/archon-main/archon/ls4
SHUTTER_MODE='open'

if [ $SUB_READOUT  == "True" ]; then
  ARCHON_CFG_LIST="northeast_1024.acf,southeast_1024.acf,northwest_1024.acf,southwest_1024.acf"
else
  ARCHON_CFG_LIST="northeast_left.acf,southeast_left.acf,northwest_left.acf,southwest_left.acf"
  #ARCHON_CFG_LIST="northeast_dp.acf,southeast_dp.acf,northwest_dp.acf,southwest_dp.acf"
fi

JSON_CFG_LIST="northeast.json,southeast.json,northwest.json,southwest.json"

# not used internally yet by ls4_ccp.py
ABORT_FILE="/tmp/abort_ls4"
if [ -e $ABORT_FILE ]; then
   rm $ABORT_FILE
fi

NAME_LIST="ctrl1,ctrl2,ctrl3,ctrl4"
ENABLE_LIST="ctrl1,ctrl2,ctrl3,ctrl4"
IP_LIST="192.168.1.1,192.168.2.1,192.168.3.1,192.168.4.1"
IP_BIND_LIST="192.168.1.10,192.168.2.10,192.168.3.10,192.168.4.10"
PORT_LIST="0,0,0,0"

SYNC="True"
CLEAR_TIME=60.0
SAVE_IMAGE="True"

python $PYTHON/run_ccp.py --ip_list $IP_LIST --conf_path $CONF_PATH --acf_list $ARCHON_CFG_LIST --map_list $JSON_CFG_LIST --image_prefix $IMG_PREFIX --exptime $EXPTIME  --enable_list $ENABLE_LIST $TEST --bind_list $IP_BIND_LIST --port_list $PORT_LIST --leader ctrl1 --sync $SYNC --log_level $LOG_LEVEL --clear_time $CLEAR_TIME --save $SAVE_IMAGE --power_down $POWER_DOWN --shutter_mode $SHUTTER_MODE --name_list $NAME_LIST --initial_clear $INITIAL_CLEAR  --idle_function $IDLE_FUNCTION --reset $RESET_FLAG --initial_reboot $REBOOT_FLAG

