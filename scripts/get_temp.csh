#!/bin/tcsh
#
# read register0 and register1 values from fits header
# and convert to deg C
#
foreach file (`ls test0_*_0.fits`)
  set reg0 = 0
  set reg1 = 0
  set startobs = `gethead $file STARTOBS`
  set l = `imhead $file  | grep -e "vcpu_outreg0"`
  set reg0 = $l[4]
  set l = `imhead $file  | grep -e "vcpu_outreg1"`
  set reg1 = $l[4]
  set t = 0
  set rtd_ohms = `echo "scale=3; ( $reg0 * 65536 + $reg1) * 244.5 / 16777216" | bc`
  if (1) then
  set t = `python $LS4_CONTROL_ROOT/scripts/rtd_convert.py $rtd_ohms`
  endif
  echo $file $startobs $reg0 $reg1 $rtd_ohms $t
end
