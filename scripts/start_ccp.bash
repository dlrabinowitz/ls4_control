#!/bin/bash
source ~/ls4_venv/bin/activate
LOG_LEVEL="INFO"
CLEAR_FLAG="False"
SUB_READOUT="False"
RESET_FLAG="False"
REBOOT_FLAG="False"
POWER_DOWN="False"
FAKE_FLAG="False"
HELP_FLAG="False"

EXPTIME=0.25
IDLE_FUNCTION='clear'

n_args=$#

index=1
reset=False
while [ $index -le $n_args ]; do
   param=$1

   if [ $param == "-help" ] ; then
      HELP_FLAG=True  

   elif [ $param == "-verbose" ] ; then
      LOG_LEVEL="DEBUG"

   elif [ $param == "-clear" ] ; then
      CLEAR_FLAG=True  

   elif [ $param == "-reset" ] ; then
      RESET_FLAG=True  

   elif [ $param == "-reboot" ] ; then
      REBOOT_FLAG=True  

   elif [ $param == "-subread" ]; then
      SUB_READOUT=True

   elif [ $param == "-poweroff" ]; then
      RESET_FLAG=True  
      POWER_DOWN=True  

   elif [ $param == "-fake" ] ; then
      FAKE_FLAG=True  
   fi

   let "index=index+1"
   shift 1
done

if [ $HELP_FLAG == "True" ]; then
   echo "syntax: start_ccp.bash [ options ]"
   echo "options:"
   echo "-verbose  : verbose messaging"
   echo "-reset    : reset controllers"
   echo "-reboot   : reboot controllers"
   echo "-poweroff : reset and power off controllers"
   echo "-fake     : fake operation of controllers"
   echo "-help     : print help"
   exit
fi

echo "LOG_LEVEL=$LOG_LEVEL CLEAR_FLAG=$CLEAR_FLAG SUB_READOUT=$SUB_REAWDOUT RESET_FLAG=$RESET_FLAG REBOOT_FLAG=$REBOOT_FLAG POWER_DOWN=$POWER_DOWN FAKE_FLAG=$FAKE_FLAG HELP_FLAG=$HELP_FLAG"


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
  #ARCHON_CFG_LIST="northeast.acf,southeast.acf,northwest.acf,southwest.acf"
  ARCHON_CFG_LIST="northeast.acf"
  #ARCHON_CFG_LIST="northeast_dp.acf,southeast_dp.acf,northwest_dp.acf,southwest_dp.acf"
fi

#JSON_CFG_LIST="northeast.json,southeast.json,northwest.json,southwest.json"
JSON_CFG_LIST="northeast.json"

# not used internally yet by ls4_ccp.py
ABORT_FILE="/tmp/abort_ls4"
if [ -e $ABORT_FILE ]; then
   rm $ABORT_FILE
fi

NAME_LIST="ctrl1"
ENABLE_LIST="ctrl1"
IP_LIST="192.168.3.1"
IP_BIND_LIST="192.168.3.10"
PORT_LIST="0"
#NAME_LIST="ctrl1,ctrl2,ctrl3,ctrl4"
#ENABLE_LIST="ctrl1,ctrl2,ctrl3,ctrl4"
#IP_LIST="192.168.1.1,192.168.2.1,192.168.3.1,192.168.4.1"
#IP_BIND_LIST="192.168.1.10,192.168.2.10,192.168.3.10,192.168.4.10"
#PORT_LIST="0,0,0,0"

#SYNC="True"
SYNC="False"
CLEAR_TIME=0.0
SAVE_IMAGE="True"

python $PYTHON/run_ccp.py --ip_list $IP_LIST --conf_path $CONF_PATH --acf_list $ARCHON_CFG_LIST --map_list $JSON_CFG_LIST --image_prefix $IMG_PREFIX --exptime $EXPTIME  --enable_list $ENABLE_LIST $TEST --bind_list $IP_BIND_LIST --port_list $PORT_LIST --leader ctrl1 --sync $SYNC --log_level $LOG_LEVEL --clear_time $CLEAR_TIME --save $SAVE_IMAGE --power_down $POWER_DOWN --shutter_mode $SHUTTER_MODE --name_list $NAME_LIST --initial_clear $CLEAR_FLAG  --idle_function $IDLE_FUNCTION --reset $RESET_FLAG --initial_reboot $REBOOT_FLAG --fake $FAKE_FLAG

