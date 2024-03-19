#!/bin/tcsh
if ( $#argv != 1 ) then
   echo "syntax: $argv[0] [data path]"
   exit
endif

cd $argv[1]
set l = `ls *.fits`
#echo $l
set n = $#l
echo $n
@ p = $n / 8
set n1 = 1
@ n2 = $n1 + $p
while ( $n2 <= $n )
  echo "gzip $n1 $n2 &"
  gzip $l[$n1-$n2] &
  if ( $n2 == $n ) then
      @ n2 = $n + 1
  else
    @ n1 = $n1 + $p
    @ n2 = $n2 + $p
    if ( $n2 > $n ) then
       set n2 = $n
    endif
  endif
end

