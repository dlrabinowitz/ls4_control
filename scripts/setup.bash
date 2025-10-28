#!usr/bin/bash

# Setup file for bash scripts when running LS4 camera code.
# This file must be sourced by "~/.bashrc" ONLY after changing
# to the root directory of the ls4_control code.

# Use the Python library at ~/observer_venv for Python.
# This library is updated with copies of the Python
# modules that comprise the ls4_control code. Use the
# "up" alias each time the source code is modified to 
# copy to the library (see ~/.bash_aliases).

# Root directoy of camera-control code (ls4_control)
LS4_CONTROL_ROOT=`pwd`
export PYTHON_VENV=~/observer_venv
source $PYTHON_VENV/bin/activate



# TCP Sockets for sending commands to camera control code 
# (ls4_control, aka "ccp")
SERVER_HOST="ls4-workstn"
SERVER_PORT=6000 # For all commands
STATUS_PORT=6001 # For status command when ccp is busy

# IPs assigned to Archon controllers 1,2,3,4
CTRL1_IP="10.0.1.1"
CTRL2_IP="10.0.2.1"
CTRL3_IP="10.0.3.1"
CTRL4_IP="10.0.4.1"

# Each controller is also assigned to a specific quadrant of the
# array
NORTHEAST_IP=$CTRL1_IP
SOUTHEAST_IP=$CTRL2_IP
NORTHWEST_IP=$CTRL3_IP
SOUTHWEST_IP=$CTRL4_IP

# BIND_IPs are the IPs of the network adapters used by ls4-workstn
# to talk to the respective controllers
CTRL1_BIND_IP="10.0.1.10"
CTRL2_BIND_IP="10.0.2.10"
CTRL3_BIND_IP="10.0.3.10"
CTRL4_BIND_IP="10.0.4.10"
     
export SERVER_PORT 
export STATUS_PORT
export LS4_CONTROL_ROOT
export CTRL1_IP
export CTRL2_IP
export CTRL3_IP
export CTRL4_IP
export NORTHEAST_IP
export SOUTHEAST_IP
export NORTHWEST_IP
export SOUTHWEST_IP
export CTRL1_BIND_IP
export CTRL2_BIND_IP
export CTRL3_BIND_IP
export CTRL4_BIND_IP

x=$LS4_CONTROL_ROOT
s=$x/scripts
p=$x/python
a=$x/archon-main/archon
c=$a/controller
l=$a/ls4
t=~/data/test



