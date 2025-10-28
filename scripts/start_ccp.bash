#!/bin/bash
# start_ccp.bash
# D. Rabinowitz 2025 Oct 13
#
# This script starts the LS4 camera server ("run_ccp.py")

# Normally start_ccp.bash is called implicitlt by
# "obs_control", which also startsscheduler.
# 
# However, for engineering tests, start_ccp.bash may also be 
# started stand-alone

#
# Engineering startup:

# Log in as "observer" on ls4-workstn and open a terminal window.
# This starts a tcsh shell (required) that sources enviromnemnt 
# ariables at # /home/observer/.login. 
#
# Then exectute ~/ls4_control/scripts/startup.bash.
# Diagnostic output is printed to the termminal.
# 
# Exposures may be takeing using the "test_loop.csh" script
# 
#

echo "PYTHON_VENV is $PYTHON_VENV"
source $PYTHON_VENV/bin/activate
cd $LS4_CONTROL_ROOT
echo "LS4_CONTROL_ROOT is $LS4_CONTROL_ROOT"
source $LS4_CONTROL_ROOT/scripts/setup.bash

echo "SERVER_HOST is $SERVER_HOST"
echo "SERVER_PORT is $SERVER_PORT"
    
if [[ -v "LS4_DATA_DIR" ]]; then
  DATA_PATH=$LS4_DATA_DIR
  echo "using DATA_PATH=$DATA_PATH"
else
  echo "environment variable LS4_DATA_DIR is not defined"
  DATA_PATH="/data/$USER"
  echo "using default DATA_PATH=$DATA_PATH"
fi

if [[ -v "FAKE_CAMERA" ]]; then
  if [ "$FAKE_CAMERA" == "1" ]; then
    FAKE_FLAG=true
  else 
    FAKE_FLAG=false
  fi
  echo "using FAKE_FLAG=$FAKE_FLAG"
else
  echo "environment variable FAKE_CAMERA is not defined"
  FAKE_CAMERA=0
  echo "using default FAKE_FLAG=$FAKE_FLAG"
fi
    
LOG_LEVEL="DEBUG"
CLEAR_FLAG=false
SUB_READOUT=false
LEFT_AMP=false
RIGHT_AMP=false
BOTH_AMP=true
RESET_FLAG=false
REBOOT_FLAG=false
POWER_DOWN=false
LOG_FLAG=false
HELP_FLAG=false
EXPTIME=0.25
IDLE_FCTN="clear"

# Abort files are created on disk to force the control code to exit. 
# When ABORT_FILE is created, any ongoing exposure is aborted but control code keeps handling more commands. When ABORT_SERVER_FILE is created, the exposure is aborted and the control code exits.

# Clear any existing instances of abort files
ABORT_EXPOSURE_FILE="/tmp/observer_ls4_abort_exposure"
ABORT_SERVER_FILE="/tmp/observer_ls4_abort_server"
      
if [ -e $ABORT_EXPOSURE_FILE ]; then
   rm -f $ABORT_EXPOSURE_FILE
fi

if [ -e $ABORT_EXPOSURE_FILE ]; then
   echo "ERROR: can not remove abort file [ $ABORT_EXPOSURE_FILE ]"
   ls -altd $ABORT_EXPOSURE_FILE
   exit
fi

if [ -e $ABORT_SERVER_FILE ]; then
   rm -f $ABORT_SERVER_FILE 
fi


if [ -e $ABORT_SERVER_FILE ]; then
   echo "ERROR: can not remove abort server file [ $ABORT_SERVER_FILE ] "
   ls -altd $ABORT_SERVER_FILE
   exit
fi
     
n_args=$#

index=1
log_file=""
while [ $index -le $n_args ]; do
   param=$1
                
   # make sure param starts with "-'
   first_char=`echo $param | cut -c 1`
   if [ "$first_char" != "-" ] ; then
      echo "ERROR: parameter $param does not start with -"
      exit
   fi

   if [ $param == "-help" ] || [ $param == "-h" ] || [ $param == "--h" ] || [ $param == "--help" ] ; then
      HELP_FLAG=true  

   elif [ $param == "-log_level" ] ; then
      let "index=index+1"
      shift 1
      LOG_LEVEL=$1

   elif [ $param == "-clear" ] ; then
      CLEAR_FLAG=true  

   elif [ $param == "-reset" ] ; then
      RESET_FLAG=true  

   elif [ $param == "-reboot" ] ; then
      REBOOT_FLAG=true  

   elif [ $param == "-subread" ]; then
      echo "subread not implemented"
      #SUB_READOUT=true

   elif [ $param == "-left" ]; then
      echo "RIGHT_AMP is $RIGHT_AMP"
      if $RIGHT_AMP; then
        echo "ERROR: Can not set both left and right amp"
        exit
      fi
      LEFT_AMP=true
      BOTH_AMP=false

   elif [ $param == "-right" ]; then
      if $LEFT_AMP; then
        echo "ERROR: Can not set both left and right amp"
        exit
      fi
      RIGHT_AMP=true
      BOTH_AMP=false

   elif [ $param == "-poweroff" ]; then
      RESET_FLAG=true  
      POWER_DOWN=true  

   elif [ $param == "-fake" ] ; then
      FAKE_FLAG=true  

   elif [ $param == "-log" ] ; then
      LOG_FLAG=true  
      let "index=index+1"
      shift 1
      log_file=$1

   elif [ $param == "-data_path" ] ; then
      let "index=index+1"
      shift 1
      DATA_PATH=$1

   elif [ $param == "-exp_time" ] ; then
      let "index=index+1"
      shift 1
      EXPTIME=$1

   elif [ $param == "-idle_fctn" ] ; then
      let "index=index+1"
      shift 1
      IDLE_FCTN=$1
   fi

   let "index=index+1"
   shift 1
done

if $HELP_FLAG; then
   echo "syntax: start_ccp.bash [ options ]"
   echo "options:"
   echo "  -log_level [level] : level of diagnostic messaging (ERROR,WARN,INFO,DEBUG)"
   echo "  -clear             : clear CCD on startup "
   echo "  -reset             : reset controllers on startup " 
   echo "  -reboot            : reboot controllers on startup"   
   echo "  -subread           : readout sub-section of each CCD" 
   echo "  -poweroff          : reset and power off controllers"
   echo "  -fake              : fake the operation of the CCD controllers "
   echo "  -log [file]        : write output messages to specified log file"
   echo "  -data_path [path]  : set directory path for saved images"
   echo "  -exp_time [expt]   : set default exposure time(sec) for exposures"
   echo "  -idle_fctn [fctn]  : set idle function between exposures (none,clear,flush)"
   echo "  -left              : Readout all CCDs through left amp"
   echo "  -right             : Readout all CCDs through right amp"
   echo "  -help              : print help"
   echo " "
   echo "defaults:"
   echo "  -log_level : $LOG_LEVEL"
   echo "  -reset     : $RESET_FLAG"
   echo "  -reboot    : $REBOOT_FLAG"
   echo "  -subread   : $SUB_READOUT"
   echo "  -poweroff  : $POWER_DOWN"
   echo "  -fake      : $FAKE_FLAG"
   echo "  -log       : standard output"
   echo "  -data_path : $DATA_PATH"
   echo "  -exp_time  : $EXPTIME"
   echo "  -idle_fctn : $IDLE_FCTN"

   exit
fi

if $BOTH_AMP; then
  AMP_DIRECTION="both"
elif $LEFT_AMP; then
  AMP_DIRECTION="left"
elif $RIGHT_AMP; then
  AMP_DIRECTION="right"
else
  echo "ERROR: amp choice is neither both, left, nor right"
  exit
fi    

#NOTE: If -log is not a parameter, then output goes to standard out.

echo "LOG_LEVEL=$LOG_LEVEL CLEAR_FLAG=$CLEAR_FLAG SUB_READOUT=$SUB_READOUT RESET_FLAG=$RESET_FLAG REBOOT_FLAG=$REBOOT_FLAG POWER_DOWN=$POWER_DOWN FAKE_FLAG=$FAKE_FLAG HELP_FLAG=$HELP_FLAG LOG_FLAG=$LOG_FLAG LOG_FILE=$log_file DATA_PATH=$DATA_PATH EXPTIME=$EXPTIME IDLE_FCTN=$IDLE_FCTN AMP_DIRECTION=$AMP_DIRECTION"
    
dt=`date +"LS4_%Y%m%d%H%M%S"`
IMG_PREFIX=$dt
CONF_PATH=$LS4_CONTROL_ROOT/conf
SCRIPTS=$LS4_CONTROL_ROOT/scripts
PYTHON=$LS4_CONTROL_ROOT/python 
LPYTHON=$LS4_CONTROL_ROOT/archon-main/archon/ls4
SHUTTER_MODE='open'
echo "PYTHON is $PYTHON"

if $SUB_READOUT; then
  ARCHON_CFG_LIST="northeast_1024.acf,southeast_1024.acf,northwest_1024.acf,southwest_1024.acf"
else
  if $BOTH_AMP; then
    ARCHON_CFG_LIST="northeast.acf,southeast.acf,northwest.acf,southwest.acf"
    CLEAR_TIME=30
  elif $LEFT_AMP; then
    ARCHON_CFG_LIST="northeast_left.acf,southeast_left.acf,northwest_left.acf,southwest_left.acf"
    CLEAR_TIME=60
  elif $RIGHT_AMP; then
    ARCHON_CFG_LIST="northeast_right.acf,southeast_right.acf,northwest_right.acf,southwest_right.acf"
    CLEAR_TIME=60
  fi
fi

JSON_CFG_LIST="northeast.json,southeast.json,northwest.json,southwest.json"


NAME_LIST="ctrl1,ctrl2,ctrl3,ctrl4"
ENABLE_LIST="ctrl1,ctrl2,ctrl3,ctrl4"
IP_LIST="$CTRL1_IP,$CTRL2_IP,$CTRL3_IP,$CTRL4_IP"
IP_BIND_LIST="$CTRL1_BIND_IP,$CTRL2_BIND_IP,$CTRL3_BIND_IP,$CTRL4_BIND_IP"

# PORTS are not reserved for the controllers
PORT_LIST="0,0,0,0"

echo "Enabled Controllers: $ENABLE_LIST"
echo "CONTROLLER IPs: $IP_LIST"
echo "IP_BIND_LIST: $IP_BIND_LIST"
echo "PORT_LIST : $PORT_LIST"
echo "AMP_DIRECTION:  $AMP_DIRECTION"

# Use synchronous I/O for controller commands (in most cases). Controllers must be wired with synchronous clock.
SYNC=true

# For dual amp readout, nominal readout time is ~20 sec. Add 10 sec extra to clear out ccd with continuous clocking.
#CLEAR_TIME=30.0

# Save all images to disk (as FITS images) after they are read out.
SAVE_IMAGE=true

# When LOG_FLAG is true, pipe the output of run_ccp.py to $log_file
if $LOG_FLAG; then

  python $PYTHON/run_ccp.py --ip_list $IP_LIST --conf_path $CONF_PATH --acf_list $ARCHON_CFG_LIST --map_list $JSON_CFG_LIST --image_prefix $IMG_PREFIX --exptime $EXPTIME  --enable_list $ENABLE_LIST $TEST --bind_list $IP_BIND_LIST --port_list $PORT_LIST --leader ctrl1 --sync $SYNC --log_level $LOG_LEVEL --clear_time $CLEAR_TIME --save $SAVE_IMAGE --power_down $POWER_DOWN --shutter_mode $SHUTTER_MODE --name_list $NAME_LIST --initial_clear $CLEAR_FLAG  --idle_function $IDLE_FCTN --reset $RESET_FLAG --initial_reboot $REBOOT_FLAG --fake $FAKE_FLAG --server_port $SERVER_PORT --status_port $STATUS_PORT --data_path $DATA_PATH --amp_direction $AMP_DIRECTION >& $log_file &

# When LOG_FLAG is false, output from run_ccp.py goes to terminal
else

  python $PYTHON/run_ccp.py --ip_list $IP_LIST --conf_path $CONF_PATH --acf_list $ARCHON_CFG_LIST --map_list $JSON_CFG_LIST --image_prefix $IMG_PREFIX --exptime $EXPTIME  --enable_list $ENABLE_LIST $TEST --bind_list $IP_BIND_LIST --port_list $PORT_LIST --leader ctrl1 --sync $SYNC --log_level $LOG_LEVEL --clear_time $CLEAR_TIME --save $SAVE_IMAGE --power_down $POWER_DOWN --shutter_mode $SHUTTER_MODE --name_list $NAME_LIST --initial_clear $CLEAR_FLAG  --idle_function $IDLE_FCTN --reset $RESET_FLAG --initial_reboot $REBOOT_FLAG --fake $FAKE_FLAG --server_port $SERVER_PORT --status_port $STATUS_PORT --data_path $DATA_PATH --amp_direction $AMP_DIRECTION

fi


# After run_ccp.py exits, clear any instance of abort files that may have been created on disk (if abort scripts were executed). 

if [ -e $ABORT_EXPOSURE_FILE ]; then
  rm $ABORT_EXPOSURE_FILE
fi

if [ -e $ABORT_SERVER_FILE ]; then
  rm $ABORT_SERVER_FILE
fi

