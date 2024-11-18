#!/bin/tcsh
# map the locations of the images for given exposure using fits keyword CCD_NAME
set q = 0
while ( $q <= 3)
  set n = 0
  while ($n <= 15)
    set f = "test"$q"_001_"$n".fits"
    #gethead $f CCD_NAME TAP_NAME
    set l = `gethead $f CCD_NAME TAP_NAME`
    echo $f $l
    @ n = $n + 1
  end
  @ q = $q + 1
end
