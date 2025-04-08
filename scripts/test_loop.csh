#!/bin/tcsh
#
# repeatedly send expose commands to ls4 control program
#
if (! -e $LS4_CONTROL_ROOT/scripts/make_mosaics.csh ) then
   echo "no make_mosaics.csh"
   exit
endif

set ls4_host = `hostname`
set CLEAR = 0
set NUM_EXP = 3    
set exptime0 = 20
set exp_incr = 0  
set shutter = "True" 
set exp_delay = 0.0

cd /home/ls4/data/test

# disk usage limit in percent
set DISK_LIMIT = 90

if ( $CLEAR == 1 ) then
  echo `date` "clearing 30 sec"
  set l = `echo "clear 30" | netcat -N $ls4_host 5000`
  echo `date` $l   
  if ( $l != "DONE") exit
endif

set l = `echo "vsub_on" | netcat -N $ls4_host 5000`
echo `date` $l   
if ( $l != "DONE") exit

echo `date` "taking $NUM_EXP  exposures"

set n = 0
@ n_last = $NUM_EXP + 1
set l = "DONE"
echo $l $n $n_last
while ( $l == "DONE" && $n < $n_last )
  set disk_usage =  `df -k /data | awk '{print $5}' | tail -n 1 | sed -e "s/%//g"`
  echo `date` "disk_usage " $disk_usage
  if ( $disk_usage > $DISK_LIMIT ) then
     echo `date` "disk_usage " $disk_usage " exceeds $DISK_LIMIT %"
     break
  endif
  set save_dir = `printf "exp_%05d" $n`
  if ( -e $save_dir ) then
     rm -rf $save_dir
  endif
  mkdir $save_dir
  @ n = $n + 1
  set exptime = `echo "scale=3; $exptime0 + $n * $exp_incr" | bc`
  if ( $n == 1 ) then
    set exp_mode = "first"
  else if ( $n == $n_last ) then
    set exp_mode = "last"
  else
    set exp_mode = "next"
  endif
  echo `date` $n $exp_mode start
  set l = `echo "expose $shutter $exptime test $exp_mode" | netcat -N $ls4_host 5000`
  echo `date` $n $exp_mode $l   
  #$LS4_CONTROL_ROOT/scripts/make_mosaics.csh testC 
  mv testC*fits $save_dir
  sleep $exp_delay
end

echo `date` "shutting down"
set l = `echo "shutdown" | netcat -N $ls4_host 5000`
echo `date` "shutting down" $l


