#!/bin/tcsh
#
# read command from standard input, pipe to ls4_ccp server
#
echo "enter 'exit' to exit"
echo ""
set l_prev = ""
while ( 0 == 0 )
  set l = `echo "$<"`
  if ( $l[1] == "exit" ) break
  if ( $l[1] == "!" ) then
      set l = "$l_prev"
  endif
  echo $l | netcat -N ls4-workstn 5000
  set l_prev = "$l"
end
echo "good bye"
