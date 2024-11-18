#!/bin/tcsh
#
# take a series of exposure pairs with increasing exposure times
# between exposure pairs in order to generate a PTC.
#
# Between pairs of exposures, exceute clean routine with 3 erase cycles and
# 10 purge cycles.
#
#
if (! -e $LS4_CONTROL_ROOT/scripts/make_mosaics.csh ) then
   echo "no make_mosaics.csh"
   exit
endif

set num_exp_pairs = 50
set exptime0 = 0.0 
set exp_incr = 0.10
set shutter = "True" 
set exp_delay = 0.0

set INITIAL_CLEAR = 1 
set INITIAL_CLEAR_TIME = 30
#
# change to 1 to erase before each exposure
set ERASE_EACH_TIME = 0
#
# change to 1 to clear before each exposure
set CLEAR_EACH_TIME = 1
set CLEARING_TIME = 10

# change to 1 to clean before each exposure
set CLEAN_EACH_TIME = 1
set CLEAR_ERASE = "True"
set CLEAR_FAST_FLUSH = "True"
set CLEAR_ERASE_CYCLES = 1
set CLEAR_FLUSH_COUNT = 2

# disk usage limit in percent
set DISK_LIMIT = 90


set command = "vsub_on"
echo `date` $command
set l = `echo $command | netcat -N ls4-workstn 5000`
echo `date` $l   
if ( $l != "DONE") exit

if ( $INITIAL_CLEAR == 1 ) then
  set command = "clear $INITIAL_CLEAR_TIME"
  echo `date` $command
  set l = `echo $command | netcat -N ls4-workstn 5000`
  echo `date` $l   
  if ( $l != "DONE") exit
endif

echo `date` "taking $num_exp_pairs  exposure pairs with exptimes incrementing by $exp_incr  from $exptime0"

@ num_exp = $num_exp_pairs * 2
@ n_final = $num_exp + 1

# l will be the reply from each command to the server. If an error occurs,
# the reply will not be "DONE". Exit the loop early if that occurs. Otherwise
# keep looping until the required number of exposures have been takem
set l = "DONE"
set n_pairs = 0
set n = 1
set n_prev = 0
while ( $l == "DONE" && $n <= $n_final )
  set disk_usage =  `df -k /data | awk '{print $5}' | tail -n 1 | sed -e "s/%//g"`
  echo `date` "disk_usage " $disk_usage
  if ( $disk_usage > $DISK_LIMIT ) then
     echo `date` "disk_usage " $disk_usage " exceeds $DISK_LIMIT %"
     break
  endif
  @ m = ( $n - 1 ) / 2
  set exptime = `echo "scale=3; $exptime0 + ( $m * $exp_incr ) " | bc`
  if ( $num_exp == 1 ) then
    set exp_mode = "single"
  else if ( $n == 1 ) then
    set exp_mode = "first"
  else if ( $n == $n_final ) then
    set exp_mode = "last"
  else
    set exp_mode = "next"
  endif

  if ( $n > $n_prev   ) then
      set n_prev = $n 
      if ( $ERASE_EACH_TIME  == 1 ) then
        set command = "erase"
        echo `date` $command
        set l = `echo $command | netcat -N ls4-workstn 5000`
        echo `date` $l   
        if ( $l != "DONE" ) then
           echo "error erasing on exposure $n"
           break
        endif
      endif

      if ( $CLEAN_EACH_TIME == 1 ) then
        set command = "clean $CLEAR_ERASE $CLEAR_ERASE_CYCLES $CLEAR_FLUSH_COUNT $CLEAR_FAST_FLUSH"
        echo `date` $command
        set l = `echo $command | netcat -N ls4-workstn 5000`
        set l = `echo $command | netcat -N ls4-workstn 5000`
        set l = `echo $command | netcat -N ls4-workstn 5000`
        echo `date` $l   
        if ( $l != "DONE" ) then  
           echo "error clearing on exposure $n"
           break
        endif
      endif

      if ( $CLEAR_EACH_TIME == 1 ) then
        set command = "clear $CLEARING_TIME"
        echo `date` $command
        set l = `echo $command | netcat -N ls4-workstn 5000`
        echo `date` $l   
        if ( $l != "DONE" ) then  
           echo "error clearing on exposure $n"
           break
        endif
      endif

  endif

  set command = "expose $shutter $exptime test $exp_mode"
  echo `date` $command
  set l = `echo $command | netcat -N ls4-workstn 5000`
  echo `date` $l   
  if ( $l != "DONE" ) then  
     echo "error taking  exposure $n"
     break
  endif

  # no data are save if exp_mode = first. These data are
  # saved while the next exposure occurs.

  if ( $exp_mode != "first" ) then
    @ m = $n - 1
    set save_dir = `printf "exp_%05d" $m`
    if ( -e $save_dir ) then
       rm -rf $save_dir
    endif
    mkdir $save_dir
    echo SAVING IN $save_dir
    #$LS4_CONTROL_ROOT/scripts/make_mosaics.csh testC 
    mv testC*fits $save_dir
  endif

  @ n = $n + 1
  sleep $exp_delay
end

echo `date` "shutting down"
set l = `echo "shutdown" | netcat -N ls4-workstn 5000`
echo `date` "shutting down" $l


