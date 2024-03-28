#!/bin/tcsh
# get noise in last read image
#
if ( $#argv == 1 ) then
   if ( -e $argv[1] ) then
      cd $argv[1]
   else
      echo "can't find path [ $argv[1] ]"
      exit
   endif
else
  cd /home/ls4/archon/ls4_control
endif

#
set l = `ls -t test3_*_15.fits | head -n 1 | sed -e "s/_/ /g" | awk '{print $2}'`
set index = "_"$l
set output_image = "mos"$index".fits"
set index = "_"$l"_"
set output_image = "mos"$index".fits"
set l = `ls test*$index*fits`
set l1 = `echo $l | sed -e "s/ /,/g"`
python /home/ls4/archon/ls4_control/scripts/get_stats.py --images $l1 --bias True


