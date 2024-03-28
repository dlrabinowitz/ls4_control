#!/bin/tcsh

if ( $#argv == 1 ) then
   if ( -e $argv[1] ) then
      cd $argv[1]
   else
      echo "path [ $argv[1] ] does not exit"
      exit
   endif
else
   cd $LS4_CONTROL_ROOT
endif

$LS4_CONTROL_ROOT/scripts/get_noise.csh `pwd` | awk '{print $2,$4,$8,$10}' >! bias.dat
$LS4_CONTROL_ROOT/scripts/get_tap_settings.csh tap_settings.dat 
python $LS4_CONTROL_ROOT/scripts/correct_tap_settings.py --bias_data bias.dat --tap_settings tap_settings.dat >! tap_corrections.dat
