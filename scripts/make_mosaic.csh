#!/bin/tcsh
#
# make mosaic image from 64 amp output of LS4 
#
set amp_selection = $CCD_AMP_SELECTION
set dark_subtract = 0
if ( $#argv != 2 && $#argv != 3 ) then
   echo "syntax: make_mosaic.csh [prefix (e.g. test)] [sequence number] [directory_path]  "
   exit
endif
if ( $#argv == 3 ) then
   if ( -e $argv[3] ) then
      cd $argv[3]
   else
      echo "directory path [ $argv[3] ] does not exist"
      exit
   endif
endif

set prefix = $argv[1]
@ n = $argv[2] + 0
if ( $dark_subtract == 1) then
  @ n_dark = $n - 1
  set dark_seq_num = `printf "_%05d_" $n_dark`
else
  set dark_seq_num = 0 
endif

set seq_num = `printf "_%05d_" $n`
echo "prefix: $prefix seq_num: $seq_num"
set output = `printf "mos_%05d.fits" $argv[2]`
echo "output: $output"

set l = `ls "$prefix"*"$seq_num"*".fits"`
set l1 = `echo $l | sed -e "s/ /,/g"`

if ( $amp_selection != "BOTH" && $amp_selection != "both" ) then
  echo "assuming left amp readout"
  set prog = "mosaic_left.py --amp_selection $amp_selection "
else
  set prog = "mosaic.py "
endif
if ( $dark_subtract == 1 ) then
  set l = `ls "$prefix"*"$dark_seq_num"*".fits"`
  set l1_dark = `echo $l | sed -e "s/ /,/g"`
  python  $LS4_CONTROL_ROOT/scripts/$prog  --images $l1 --output $output  --dark_images $l1_dark --bias False
else
  python  $LS4_CONTROL_ROOT/scripts/$prog  --images $l1 --output $output  --bias True --dark_images=""
  #python  $LS4_CONTROL_ROOT/scripts/$prog  --images $l1 --output $output  --bias False --dark_images=""
endif

#python  $LS4_CONTROL_ROOT/scripts/mosaic.py  --images $l1 --output $output  



