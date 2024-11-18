#!/bin/tcsh
#
# for each directory begining "exp_", change to that
# directory and run "$x/scripts/make_mosaics.csh testC"
#
set d0 = `pwd`
foreach d (`ls -d exp_*`)
  cd $d
  $LS4_CONTROL_ROOT/scripts/make_mosaics.csh testC
  cd $d0
end
