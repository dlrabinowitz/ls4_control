#!/bin/tcsh
#
# make mosaic image from 64 amp output of LS4 
#
if ( $#argv != 2 && $#argv != 3 ) then
   echo "syntax: make_mosaic.csh [prefix (e.g. "test")] [sequence number] [directory_path]"  "
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
set seq_num = `printf "_%03d_" $argv[2]`
echo "prefix: $prefix seq_num: $seq_num"
set output = `printf "mos_%03d.fits" $argv[2]`
echo "output: $output"

set l = `ls "$prefix"*"$seq_num"*".fits"`
echo "l: $l"
set l1 = `echo $l | sed -e "s/ /,/g"`
echo "l1: $l1"

python  $LS4_CONTROL_ROOT/scripts/mosaic.py  --images $l1 --output $output  --bias True
#python  $LS4_CONTROL_ROOT/scripts/mosaic.py  --images $l1 --output $output  



