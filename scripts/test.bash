#!/bin/bash
source ~/ls4_venv/bin/activate
EXPTIME=1.0
NUM_EXPOSURES=1
IMG_PREFIX=ls4_sw_eng
CONF_PATH=$LS4_CONTROL_ROOT/conf
SCRIPTS=$LS4_CONTROL_ROOT/scripts
PYTHON=$LS4_CONTROL_ROOT/python 
ARCHON_CFG_LIST="test_nw.acf,test_sw.acf,test_se.acf,test_ne.acf"
#ARCHON_CFG_LIST="test_nw1.acf,test_sw1.acf,test_se1.acf,test_ne1.acf"
JSON_CFG_LIST="test_nw.json,test_sw.json,test_se.json,test_ne.json"
#TEST="--test"
TEST=""
ENABLE_LIST="ctrl1,ctrl2,ctrl3,ctrl4"
#ENABLE_LIST="ctrl1,ctrl2,ctrl3"
IP_LIST="192.168.1.1,192.168.2.1,192.168.3.1,192.168.4.1"
IP_BIND_LIST="192.168.1.10,192.168.2.10,192.168.3.10,192.168.4.10"
#PORT_LIST="60021,60012,60013,60014"
PORT_LIST="0,0,0,0"

python $PYTHON/test_controller.py --ip_list $IP_LIST --conf_path $CONF_PATH --acf_list $ARCHON_CFG_LIST --map_list $JSON_CFG_LIST --prefix $IMG_PREFIX --exptime $EXPTIME --num_exp $NUM_EXPOSURES --enable_list $ENABLE_LIST $TEST --bind_list $IP_BIND_LIST --port_list $PORT_LIST

