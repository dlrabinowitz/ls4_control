#!/bin/tcsh
#
# repeatedly send expose commands to ls4 control program
#
# define host and user specific parameters

if ( ! $?USER ) then
  echo "ERROR: envirnonment variable USER is not defined"
  exit
endif

if ( $USER != "observer" ) then
  echo "ERROR: Only user observer can run this script"
  exit
endif

if ( ! $?LS4_DATA_DIR) then
  echo "ERROR: envirnonment variable LS4_DATA_DIR is not defined"
  exit
endif

if ( ! $?CCP_HOST ) then
  echo "ERROR: envirnonment variable CCP_HOST is not defined"
  exit
endif

if ( ! $?CCP_PORT ) then
  echo "ERROR: envirnonment variable CCP_PORT is not defined"
  exit
endif

set data_root = $LS4_DATA_DIR

# make sure $data_root exists
if ( ! -e $data_root ) then
   echo "ERROR: can't find root data directory at [$data_root]"
   exit
endif

# disk usage limit in percent. 
set DISK_LIMIT = 90

# set default wait-time (sec) for clearing the array
set CLEAR_TIME = 30
if ( $CCD_AMP_SELECTION != "both" ) then
  @ CLEAR_TIME = $CLEAR_TIME * 2
endif

# set defaults for  command line arguments
set clear_flag = 1  # always clear when first starting loop
set num_exp = 1 # take only a single exposure
set exptime0 = 2.0 # exposure time is 2.0 sec
set exp_incr = 0 # increment exposure time by 0 sec
set shutter_flag = 1 # open the shutter during exposures
set exp_delay = 0.0 # wait 0 sec between exposures
set prefix = "test" # prefix each fits-image name with "test"
set wait_transfer = 1 # wait for full transfer of image between exposures
set ls4_shutdown = 0 # at the end of the loop, shut down the camera

# make sure make_mosaics script exists

if (! -e $LS4_CONTROL_ROOT/scripts/make_mosaics.csh ) then
   echo "no make_mosaics.csh"
   exit
endif

# set up data dir at $data_root/yyyymmdd where data_root is defined
# above and yyyymmdd is the appropriate date (i.e. the current local 
# date if the local time < 08:00 AM, otherwise the local date plus
# one day).
# 
set tonight = `get_ut_date`
set data_dir = "$data_root/$tonight"
if ( ! -e $data_dir ) then
   mkdir $data_dir
endif


# get command-line variables if specified

# If number of specified command-line arguments is not 6 (and not ) then exit
if ( $#argv == 0 ) then
  echo "use loop_tcsh.csh --help"
  exit
else if ( $#argv == 1  ||  "$argv[1]" == "--help" || "$argv[1]" == "-h" ) then
  echo "syntax: test_loop.csh OPTIONS"
  echo "where options are:"
  echo " "
  echo "  --shutter_flag [0 or 1] --exptime [value in sec] --fits_prefix [string]  --data_dir [string] --clear_flag[0 or 1] --num_exposures [int] --wait_transfer [0 or 1] --ls4_shutdown [ 0 or 1]"
  echo " "
  echo "The options may also be specified by  -s -e -p -d -c -n -w -l, respectively."
  echo " "
  echo "The default values are:"
  echo "  shutter_flag = $shutter_flag"
  echo "  exptime0 = $exptime0"
  echo "  prefix = $prefix"
  echo "  data_dir = $data_dir"
  echo "  clear_flag = $clear_flag"
  echo "  num_exp" = "$num_exp"
  echo "  wait_transfer = $wait_transfer"
  echo "  ls4_shutdown = $ls4_shutdown"
  exit
endif

set i = 1
set j = 2
while ( $i < $#argv && $j <= $#argv )
  set arg_name = `printf "$argv[$i]" |  sed -e "s/-//g"`
  set arg_val = $argv[$j]
  #echo $i $j
  #echo "$argv[$i] $argv[$j]"
  #echo "$arg_name $arg_val"
  if ( $arg_name == "shutter_flag" || $arg_name == "s" ) then
     set shutter_flag = $arg_val
  else if ( $arg_name == "exptime" || $arg_name == "e" ) then
     set exptime0 = $arg_val
  else if ( $arg_name == "fits_prefix" || $arg_name == "p" ) then
     set prefix = $arg_val
  else if ( $arg_name == "data_dir" || $arg_name == "d" ) then
     set data_dir = $arg_val
  else if ( $arg_name == "clear_flag" || $arg_name == "c" ) then
     set clear_flag = $arg_val
  else if ( $arg_name == "num_exposures" || $arg_name == "n" ) then
     set num_exp = $arg_val
  else if ( $arg_name == "wait_transfer" || $arg_name == "w" ) then
     set wait_transfer = $arg_val
  else if ( $arg_name == "ls4_shutdown" || $arg_name == "l" ) then
     set ls4_shutdown = $arg_val
  else
     echo "ERROR unrecognized command-line argument: [ $arg_name ]"
     exit
  endif
  @ i = $i + 2
  @ j = $j + 2
end


if ( ! -e $data_dir ) then
   echo "data_dir [ $data_dir ] does not exist"
   exit
endif
  
echo "shutter_flag = $shutter_flag"
echo "exptime0 = $exptime0"
echo "prefix = $prefix"
echo "data_dir = $data_dir"
echo "clear_flag = $clear_flag"
echo "num_exp  = $num_exp"
echo "wait_transfer = $wait_transfer"
echo "ls4_shutdown = $ls4_shutdown"

echo "data will be saved at $data_dir"

if ( $shutter_flag == 0 ) then
  set shutter_flag = "False"
else
  set shutter_flag = "True"
endif

if ( $clear_flag == 1 ) then
  echo `date` "clearing $CLEAR_TIME sec"
  set l = `echo "clear $CLEAR_TIME" | netcat -N $CCP_HOST $CCP_PORT`
  echo `date` $l   
  if ( $l != "DONE") exit
endif

echo `date` "turning Vsub on"
set l = `echo "vsub_on" | netcat -N $CCP_HOST $CCP_PORT`
echo `date` $l   
if ( $l != "DONE") exit

echo `date` "taking $num_exp  exposures"

# If not waiting for transferds between exposures, then take one extra
# exposure at the end of the loop (exp_mode = last ) to transfer the
# previous exposure

if ( $wait_transfer == 0 )then
  @ n_last = $num_exp + 1
else
  set n_last = $num_exp
endif


set n = 0
set l = "DONE"
#echo $l $n $n_last
while ( $l == "DONE" && $n < $n_last )
  set disk_usage =  `df -k /data | awk '{print $5}' | tail -n 1 | sed -e "s/%//g"`
  echo `date` "disk_usage " $disk_usage
  if ( $disk_usage > $DISK_LIMIT ) then
     echo `date` "disk_usage " $disk_usage " exceeds $DISK_LIMIT %"
     break
  endif

  # prev_n is the exposure index of previous exposure (prev_n = 0 for
  # the first exposure )
  set prev_n = $n
  @ n = $n + 1
  set exptime = `echo "scale=3; $exptime0 + $n * $exp_incr" | bc`

  if ( $wait_transfer == 1 ) then
    set exp_mode = "single"
  else if ( $n == 1 ) then
    set exp_mode = "first"
  else if ( $n == $n_last ) then
    set exp_mode = "last"
  else
    set exp_mode = "next"
  endif

  # When using "single" exp_mode, the image data retrieved by
  # the expose command correspond to the current exposure index (n).
  # For exp_mode "next" and "last", the retrieved image data 
  # correspond to  the previous exposure index (prev_n).
  # For exp_mode "first", no image data are retrieved

 
  if ( $exp_mode == "first" ) then
     set save_dir = "none"
  else if ( $exp_mode == "single" ) then
     set save_dir = `printf "$data_dir/exp_%05d" $n`
  else
     set save_dir = `printf "$data_dir/exp_%05d" $prev_n`
  endif

  if ( $exp_mode != "first" ) then
    if ( -e $save_dir  ) then
       echo `date ` "over-writing save directory at [ $save_dir ]"
       rm -rf $save_dir
    endif
    mkdir $save_dir
  endif

  echo `date` " start exposure: $n mode: $exp_mode exptime: $exptime "
  set l = `echo "expose $shutter_flag $exptime $prefix $exp_mode" | netcat -N $CCP_HOST $CCP_PORT`
  echo `date` " done exposure: $n mode: $exp_mode exptime: $exptime  response: [ $l ]" 

  # check if any image data were created. If so, move them to the save_dir.
  set n_files = `ls $data_root/"$prefix"C*fits | wc -l |& grep -ve "No match"`
  if ( $n_files > 0 && $save_dir != "none" ) then
     echo `date` "moving the image data from exposure $prev_n to $save_dir"
     mv $data_root/"$prefix"C*fits $save_dir
  else
     echo `date` "no new fits files generate for exposure $n"
  endif
  echo `date` "sleeping $exp_delay sec"
  sleep $exp_delay
end


if ( $ls4_shutdown ) then
  echo `date` "shutting down"
  set l = `echo "shutdown" | netcat -N $CCP_HOST $CCP_PORT`
  echo `date` "done shutting down" $l
endif


