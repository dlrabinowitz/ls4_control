#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2021-01-20
# @Filename: __init__.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

__all__ = [
    "ArchonController",
    "ArchonCommandStatus",
    "ArchonCommand",
    "ArchonCommandReply",
    "ModType",
    "ControllerStatus"
    "LS4Controller"
    "LS4_Device"
]


MAX_COMMAND_ID = 0xFF
MAX_CONFIG_LINES = 16384

from .command import ArchonCommand, ArchonCommandReply, ArchonCommandStatus
from .controller import ArchonController
from .maskbits import ControllerStatus, ModType


#######
# added by D. Rabinowitz

FOLLOWER_TIMEOUT_MSEC = 10000
AMPC_PER_CCD = 2
CCDS_PER_QUAD = 8

# Note +/-100 V supply voltages changed to +/- 50.0 V by G. Bredthauer
# 2024 Feb 16 to keep op-amp on XV BIASS from overheating. THis change
# prevents operation of DECam CCDS with Vsub > 40.0 V
P100_SUPPLY_VOLTAGE = 50.0
N100_SUPPLY_VOLTAGE = -50.0

