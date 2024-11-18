#!/bin/tcsh
set z = $LS4_CONTROL_ROOT/scripts

if ( $#argv != 1 ) then
  echo "syntax: make_mosaic.csh [prefix]"
  exit
endif

set prefix = $argv[1]

foreach file (`ls "$prefix"0_*_01.fits`)
  set l = `echo $file | sed -e "s/$prefix//g" | sed -e "s/_/ /g"`
  set index = $l[2]
  set root = $prefix
  @ i = $index + 0
  set f = `printf "mos_%05d.fits" $i`
  if ( ! -e $f ) then
    $z/make_mosaic.csh $root $i `pwd`
  endif
end
