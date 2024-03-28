#!/bin/tcsh
#
# change gain settings for each ACF file
#
if ( $#argv != 2 ) then
   echo "syntax: change_gain_settings.csh [new gain value] [conf path]"
   exit
endif

set new_gain = $argv[1]
set conf_path = $argv[2]

if ( ! -e $conf_path ) then
   echo "conf path [ $conf_path ] does not exist"
   exit
endif

cd $conf_path

foreach file (`ls *.acf` )
  set i = 0
  while ( $i < 15 )
    set tap_line = "TAPLINE"$i
    set l = `grep -e "$tap_line=" $file | sed -e "s/=/ /g"`
    # TAPLINE11 "AD9R, 4, -564"
    sed -e "s/R, $l[3] /R, $new_gain, /g" $file >! tmp
    sed -e "s/L, $l[3] /L, $new_gain, /g" tmp >! $file
    @ i = $i + 1
  end
end

