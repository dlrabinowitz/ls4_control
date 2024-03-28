#!/bin/tcsh

if ( $#argv != 1 ) then
   echo "syntax: get_tap_settings.csh [ output_file ]"
   exit
endif
set tap_file = $argv[1]

cd $LS4_CONTROL_ROOT
grep TAP conf/*ne*acf | sed -e "s/=/ /g" | sed -e s"/,/ /g" |  awk '{print "ne",$1,$2,$3,$4}' | grep -ve "TAPLINES 16" >! $tap_file
grep TAP conf/*nw*acf | sed -e "s/=/ /g" | sed -e s"/,/ /g" |  awk '{print "nw",$1,$2,$3,$4}' | grep -ve "TAPLINES 16" >> $tap_file
grep TAP conf/*se*acf | sed -e "s/=/ /g" | sed -e s"/,/ /g" | awk '{print "se",$1,$2,$3,$4}' | grep -ve "TAPLINES 16" >> $tap_file
grep TAP conf/*sw*acf | sed -e "s/=/ /g" | sed -e s"/,/ /g" | awk '{print "sw",$1,$2,$3,$4}' | grep -ve "TAPLINES 16" >> $tap_file
