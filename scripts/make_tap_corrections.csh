#!/bin/tcsh
# make_tap_corrections.csh
#
# give tap corrections in an input file with the format described below, modify the
# archon config files in the specifed conf path
#
# input file format:
#   # NE 08979 13220   2  1989.500
#   TAPLINE0="AD3L, 2, 15209"
#   # NE 00672 09393   2  -2164.000
#   TAPLINE10="AD10L, 2, 7229"
#   # NE 09215 00719   2  2107.500
#   TAPLINE11="AD9R, 2, 2826"
#   ....
#   # SW 00624 09378   2  -2188.000
#   TAPLINE0="AD3L, 2, 7190"
#   # SW 02292 07708   2  -1354.000
#   TAPLINE10="AD10L, 2, 6354"
#   # SW 07824 02175   2  1412.000
#   ...
#   min : 57 000210  bias: 14583.000  noise:   2.248 old_offset: -04582
#   max : 8 027496  bias: 16817.000  noise:   2.166 old_offset: 021588

if ( $#argv != 2 ) then
   echo "syntax: make_tap_corrections.csh [correction file] [config path]"
   exit
endif

set conf_path = $argv[2]
if ( ! -e $conf_path ) then
   echo "can't find conf path [$conf_path]"
   exit
endif
cd $conf_path

set input = $argv[1]
if ( ! -e $input ) then
   echo "can't find input file [$input]"
   exit
endif

set nw_acf = `ls *_nw_*.acf`
set ne_acf = `ls *_ne_*.acf`
set sw_acf = `ls *_sw_*.acf`
set se_acf = `ls *_se_*.acf`

set n = `cat $input | wc -l`
set i = 1
while ( $i <= $n )
   set l = `head -n $i $input | tail -n 1`
   set  skip = 0
   if ( $#l > 2 ) then
     set quad =  $l[2]
     if ( $quad == "NW" ) then
       set acf_file = $nw_acf
     else if ( $quad == "NE" ) then
       set acf_file = $ne_acf
     else if ( $quad == "SW" ) then
       set acf_file = $sw_acf
     else if ( $quad == "SE" ) then
       set acf_file = $se_acf
     else
       set skip = 1
     endif
   endif

   if ( $skip == 0 ) then
       @ i = $i + 1

       set tap_entry = `head -n $i $input | tail -n 1 | sed -e "s/=/ /g" `
       set tap_label = $tap_entry[1]
       set tap_entry_old = `grep  "$tap_label""=" $acf_file | sed -e "s/=/ /g"`
       #echo $acf_file $tap_label : change  [ $tap_entry_old[2] $tap_entry_old[3] $tap_entry_old[4] ] to [ $tap_entry[2] $tap_entry[3] $tap_entry[4] ]
       sed -e "s/$tap_entry_old[2] $tap_entry_old[3] $tap_entry_old[4]/$tap_entry[2] $tap_entry[3] $tap_entry[4]/g" $acf_file > /tmp/dlr.temp
       cp /tmp/dlr.temp $acf_file
   endif

   @ i = $i + 1
end
