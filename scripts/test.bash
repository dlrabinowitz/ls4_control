#!/bin/bash
#
# This script starts up the LS4 control program.
# This scripts initialized configuration arguments required by
# the control program at start up, and then launches the control
# program.
#
# Commands to the program must be sent over a socket connection to the
# host machine at port 5000:
# For example, after running this script, execute
#    echo "help" | netcat -N [hostname] 5000.
# This will return are message to the terminal with the commands understood
# by the control program and their arguments.

# activate the python environment required by the control program
source ~/ls4_venv/bin/activate

# if FAKE is False, then real controllers must be connected and ready for communication.
# If Fake is True, the the controller function will be simulated
FAKE="False"

# LOG_LEVEL can be "INFO" (less verbose), "DEBUG" (most verbose), "ERROR" (only error messages) or "WARN" (only warnings and errors)
LOG_LEVEL="INFO"

# default exptime (sec) if not specified elsewhere
EXPTIME=0.50

# default prefix for saved images
IMG_PREFIX="test"

# path to Archon controller configuration files
CONF_PATH=$LS4_CONTROL_ROOT/conf

# path to python scripts
PYTHON=$LS4_CONTROL_ROOT/python 

# names of Archon controller configuration files for controllers
# named "ctr1","ctrl2","ctrl3","ctrl4"
ARCHON_CFG_LIST="test_ne.acf,test_se.acf,test_nw.acf,test_sw.acf"

# corresponding names of JSON config files describing CCD placement
# and ID's for each controller. 
JSON_CFG_LIST="test_ne.json,test_se.json,test_nw.json,test_sw.json"

# corresponding IP address for the controllers
IP_LIST="192.168.1.1,192.168.2.1,192.168.3.1,192.168.4.1"

# corresponding IP address for host networks bound to each controller
IP_BIND_LIST="192.168.1.10,192.168.2.10,192.168.3.10,192.168.4.10"

# list of enabled controllers by name
ENABLE_LIST="ctrl1,ctrl2,ctrl3,ctrl4"

# list of port numbers  to bind to the host network address listed in IP_BIND_LIST.
# These port numbers must be 0, or else match the port IDs on the controllers. 
# If  the port numbers are "0", then no local network addresses are bound. This
# allows immediate socket connections to the controllers if the control program is interrupted
# and restarted. Otherwise, there may be  a system-dependent delay before socket connections
# can be re-established.

PORT_LIST="0,0,0,0"
#PORT_LIST="4242,4242,4242,4242"

# Path to directory where FITs file will be written
DATA_PATH="/data/ls4/test"

# IF SYNC is True, the controller readouts will be synchronized using the sync-cable connecting
# the controllers. Otherwise, the readouts will be asynchronous, possibly increasing the noise
# level at readout.
SYNC="True" 

# When the controller program starts up, the controllers are initially flushed to allows residual
# charge to be cleared. The FLUSH_TIME should be longer than the readout time.
FLUSH_TIME=3.0

# Save images disk disk if True
SAVE_IMAGE="True"

# Power down the CCD biases when exiting the control program
POWER_DOWN="True"

# The path to an abort file that must be created when the controller is stuck in an event loop and
# must be aborted.
ABORT_FILE="/tmp/abort_ls4"

# The abort file must not exist when the control program is started
rm $ABORT_FILE

# make sure the data path exists
if [ ! -e $DATA_PATH ] ; then
  mkdir $DATA_PATH
fi

# the name of the control program
prog=ls4_ccp.py

# start the control program. It will not exit until there is an unrecoverable error, the abort file is
# created, or a "shutdown" command is sent to the control program.

python $PYTHON/$prog --ip_list $IP_LIST --conf_path $CONF_PATH --acf_list $ARCHON_CFG_LIST --map_list $JSON_CFG_LIST --image_prefix $IMG_PREFIX --exptime $EXPTIME --enable_list $ENABLE_LIST $TEST --bind_list $IP_BIND_LIST --port_list $PORT_LIST --leader ctrl1 --sync $SYNC --log_level $LOG_LEVEL --flush_time $FLUSH_TIME --save $SAVE_IMAGE --power_down $POWER_DOWN --data_path $DATA_PATH --fake $FAKE

