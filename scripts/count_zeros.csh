#!/bin/tcsh

set d = `pwd`
foreach file (`ls test0_*_15.fits`)
  set l = `echo $file | sed -e "s/_/ /g"`
  @  n = $l[2] + 0
  set l = ` scripts/make_mosaic.csh test $n $d | grep rms | awk '{print $2,$10}' | grep -e "000.000" | wc -l`
  echo $n $l[1]
end
