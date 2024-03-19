#!/bin/tcsh
#
# get noise in last read image
#
cd /home/ls4/archon/ls4_control
set l = `ls -t test3_*_15.fits | head -n 1 | sed -e "s/_/ /g" | awk '{print $2}'`
set index = "_"$l"_"
set output_image = "mos"$index".fits"
set l = `ls *$index*fits`
set l1 = `echo $l | sed -e "s/ /,/g"`
python scripts/get_stats.py --images $l1
python scripts/mosaic.py --images $l1 --output $output_image --bias True


