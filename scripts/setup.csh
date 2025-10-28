#!/bin/tcsh 
source ~/observer_venv/bin/activate.csh
setenv LS4_CONTROL_ROOT  `pwd`
set x = $LS4_CONTROL_ROOT
set s = $x/scripts
set p = $x/python
set a = $x/archon-main/archon
set c = $a/controller
set l = $a/ls4


