#!/bin/tcsh
#
# autotune tap settings to obtain same bias level for all amps
#
if ( $#argv != 2 ) then
   echo "syntax: autotune.csh gain iterations"
   exit
endif
set gain = $argv[1]
set n_iterations = $argv[2]

set x = $LS4_CONTROL_ROOT
set z = $x/scripts
set t = $x/../tests
set c = $x/conf

if ( ! -e $t ) then
   mkdir $t
endif

cd $c
cp test/*acf .
$z/change_gain_settings.csh $gain `pwd`
grep TAPLINE *acf

cd $x
set trial = 1
while ( $trial <= $n_iterations )
  cd $x
  set trial_dir = "trial"$trial
  echo "################# trial $trial"
  $z/test.bash 
  $z/get_tap_corrections.csh  `pwd`
  grep rms tap_corrections.dat
  if ( -e $t/$trial_dir ) then
     rm -rf $t/$trial_dir
  endif
  mkdir $t/$trial_dir
  cp *dat *fits $t/$trial_dir
  cp tap_corrections.dat $c
  rm *dat *fits
  cd $c
  $z/make_tap_corrections.csh tap_corrections.dat `pwd`
  cd $x
  echo "################# "
  @ trial = $trial + 1
end
  
   
