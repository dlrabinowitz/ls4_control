#!/bin/tcsh
#
# repeatedly send expose commands to ls4 control program
#
if (! -e $LS4_CONTROL_ROOT/scripts/make_mosaics.csh ) then
   echo "no make_mosaics.csh"
   exit
endif

set CLEAR = 1

set MAX_EXPTIME = 700
set exptime0 = 0
set exp_incr = 20 
set shutter = "True" 
set exp_delay = 0.0

# disk usage limit in percent
set DISK_LIMIT = 90

if ( $CLEAR == 1 ) then
  echo `date` "clearing 30 sec"
  set l = `echo "clear 30" | netcat -N ls4-workstn 5000`
  echo `date` $l   
  if ( $l != "DONE") exit
endif

set l = `echo "vsub_on" | netcat -N ls4-workstn 5000`
echo `date` $l   
if ( $l != "DONE") exit

echo `date` "starting"

set n = 0
set l = "DONE"
set sequence_done = 0
while ( $l == "DONE" && $sequence_done == 0)
  set disk_usage =  `df -k /data | awk '{print $5}' | tail -n 1 | sed -e "s/%//g"`
  echo `date` "disk_usage " $disk_usage
  if ( $disk_usage > $DISK_LIMIT ) then
     echo `date` "disk_usage " $disk_usage " exceeds $DISK_LIMIT %"
     break
  endif
  @ n = $n + 1
  @ m = $n - 1
  @ m = $m / 2
  set save_dir = `printf "exp_%05d" $n`
  if ( -e $save_dir ) then
     rm -rf $save_dir
  endif
  mkdir $save_dir
  set exptime = `echo "scale=3; $exptime0 + $m * $exp_incr" | bc`
  set sequence_done =  `echo "if ( $exptime > $MAX_EXPTIME ) 1 else 0" | bc`
  echo `date` "exp $n exptime $exptime"
  if ( $n == 1 ) then
    set exp_mode = "first"
  else if ( $sequence_done == 1 ) then
    set exp_mode = "last"
  else
    set exp_mode = "next"
  endif
  echo `date` $n $exp_mode start
  set l = `echo "expose $shutter $exptime test $exp_mode" | netcat -N ls4-workstn 5000`
  echo `date` $n $exp_mode $l   
  #$LS4_CONTROL_ROOT/scripts/make_mosaics.csh testC 
  mv testC*fits $save_dir
  sleep $exp_delay
end

echo `date` "shutting down"
set l = `echo "shutdown" | netcat -N ls4-workstn 5000`
echo `date` "shutting down" $l


