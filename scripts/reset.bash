#!/bin/bash
source ~/ls4_venv/bin/activate
LOG_LEVEL="DEBUG"
EXPTIME=0.05
INITIAL_CLEAR="True"
IDLE_FUNCTION="clear"

dt=`date +"LS4_%Y%m%d%H%M%S"`
IMG_PREFIX=$dt
CONF_PATH=$LS4_CONTROL_ROOT/conf
SCRIPTS=$LS4_CONTROL_ROOT/scripts
PYTHON=$LS4_CONTROL_ROOT/python 
LPYTHON=$LS4_CONTROL_ROOT/archon-main/archon/ls4
SHUTTER_MODE='open'

ARCHON_CFG_LIST="test_ne.acf,test_se.acf,test_nw.acf,test_sw.acf"
JSON_CFG_LIST="test_ne.json,test_se.json,test_nw.json,test_sw.json"

# not used
ABORT_FILE="/tmp/abort_ls4"

NAME_LIST="ctrl1,ctrl2,ctrl3,ctrl4"
ENABLE_LIST="ctrl1,ctrl2,ctrl3,ctrl4"
IP_LIST="192.168.1.1,192.168.2.1,192.168.3.1,192.168.4.1"
IP_BIND_LIST="192.168.1.10,192.168.2.10,192.168.3.10,192.168.4.10"
PORT_LIST="0,0,0,0"

SYNC="True"
CLEAR_TIME=0.0
SAVE_IMAGE="True"
POWER_DOWN=$1
RESET="True"

python $PYTHON/run_ccp.py --ip_list $IP_LIST --conf_path $CONF_PATH --acf_list $ARCHON_CFG_LIST --map_list $JSON_CFG_LIST --image_prefix $IMG_PREFIX --exptime $EXPTIME  --enable_list $ENABLE_LIST $TEST --bind_list $IP_BIND_LIST --port_list $PORT_LIST --leader ctrl1 --sync $SYNC --log_level $LOG_LEVEL --clear_time $CLEAR_TIME --save $SAVE_IMAGE --power_down $POWER_DOWN --shutter_mode $SHUTTER_MODE --name_list $NAME_LIST --initial_clear $INITIAL_CLEAR  --reset $RESET --idle_function $IDLE_FUNCTION

