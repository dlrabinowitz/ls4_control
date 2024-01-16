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
]


MAX_COMMAND_ID = 0xFF
MAX_CONFIG_LINES = 16384

from .command import ArchonCommand, ArchonCommandReply, ArchonCommandStatus
from .controller import ArchonController
from .maskbits import ControllerStatus, ModType
