#!/bin/bash
source ~/ls4_venv/bin/activate
LOG_LEVEL="INFO" 
EXPTIME=0.000
NUM_EXPOSURES=0
IMG_PREFIX=ls4_sw_eng
CONF_PATH=$LS4_CONTROL_ROOT/conf
SCRIPTS=$LS4_CONTROL_ROOT/scripts
PYTHON=$LS4_CONTROL_ROOT/python 
ARCHON_CFG_LIST="test_ne.acf,test_se.acf,test_nw.acf"
JSON_CFG_LIST="test_ne.json,test_se.json,test_nw.json"
TEST=""

ENABLE_LIST="ctrl1,ctrl2,ctrl3,ctrl4"
IP_LIST="192.168.1.1,192.168.2.1,192.168.3.1"
IP_BIND_LIST="192.168.1.10,192.168.2.10,192.168.3.10"
PORT_LIST="0,0,0"
SYNC=False
#POWER_DOWN=True 
#
# POWER_DOWN to protect CCDS, especially when autoflush is not running when script ends
#POWER_DOWN=True 
# If config files have "ContinuousExpose=1", the the ccds will be left
# powered up and continuously reading out if POWER_DOWN=False.
# Otherwise, they will be left continuously reading out and will be powered down
# while still reading out.
POWER_DOWN="False"


if [ $# -eq 0  ]; then
   echo "no arg"
elif [ $1 == "False" ]; then
   POWER_DOWN=False
elif [ $1 == "True" ]; then
   POWER_DOWN=True
fi


python $PYTHON/test_controller.py --ip_list $IP_LIST --conf_path $CONF_PATH --acf_list $ARCHON_CFG_LIST --map_list $JSON_CFG_LIST --prefix $IMG_PREFIX --exptime $EXPTIME --num_exp $NUM_EXPOSURES --enable_list $ENABLE_LIST $TEST --bind_list $IP_BIND_LIST --port_list $PORT_LIST --leader "ctrl1" --sync $SYNC --log_level $LOG_LEVEL --power_down $POWER_DOWN

