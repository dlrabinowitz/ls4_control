#!/bin/bash
source ~/ls4_venv/bin/activate
LOG_LEVEL="INFO"
EXPTIME=20.0
EXPINCR=0.0
NUM_EXPOSURES=101
IMG_PREFIX=ls4_sw_eng
CONF_PATH=$LS4_CONTROL_ROOT/conf
SCRIPTS=$LS4_CONTROL_ROOT/scripts
PYTHON=$LS4_CONTROL_ROOT/python 
ARCHON_CFG_LIST="test_ne.acf,test_se.acf,test_nw.acf,test_sw.acf"
JSON_CFG_LIST="test_ne.json,test_se.json,test_nw.json,test_sw.json"

# swap NE/SE
#ARCHON_CFG_LIST="test_se_20240118.acf,test_ne_20240118.acf,test_nw_20240118.acf,test_sw_20240118.acf"
#JSON_CFG_LIST="test_se.json,test_ne.json,test_nw.json,test_sw.json"

# swap NW/SW
#ARCHON_CFG_LIST="test_ne_20240118.acf,test_se_20240118.acf,test_sw_20240118.acf,test_nw_20240118.acf"
#JSON_CFG_LIST="test_ne.json,test_se.json,test_sw.json,test_nw.json"
TEST=""
ABORT_FILE="/tmp/abort_ls4"
rm $ABORT_FILE

ENABLE_LIST="ctrl1,ctrl2,ctrl3,ctrl4"
IP_LIST="192.168.1.1,192.168.2.1,192.168.3.1,192.168.4.1"
IP_BIND_LIST="192.168.1.10,192.168.2.10,192.168.3.10,192.168.4.10"
PORT_LIST="0,0,0,0"

#ENABLE_LIST="ctrl1"
#IP_LIST="192.168.1.1"
#IP_BIND_LIST="192.168.1.10"
#PORT_LIST="0"

SYNC="True"
CLEAR_TIME=3.0
SAVE_IMAGE="True"
POWER_DOWN="True"

python $PYTHON/test_controller.py --ip_list $IP_LIST --conf_path $CONF_PATH --acf_list $ARCHON_CFG_LIST --map_list $JSON_CFG_LIST --prefix $IMG_PREFIX --exptime $EXPTIME --exp_incr $EXPINCR --num_exp $NUM_EXPOSURES --enable_list $ENABLE_LIST $TEST --bind_list $IP_BIND_LIST --port_list $PORT_LIST --leader ctrl1 --sync $SYNC --log_level $LOG_LEVEL --clear_time $CLEAR_TIME --save $SAVE_IMAGE --power_down $POWER_DOWN

