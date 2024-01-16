#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2021-01-22
# @Filename: maskbits.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from __future__ import annotations

import enum


__all__ = ["ModType", "ControllerStatus", "ArchonPower"]


class ModType(enum.Enum):
    """Module type codes."""

    NONE = 0
    DRIVER = 1
    AD = 2
    LVBIAS = 3
    HVBIAS = 4
    HEATER = 5
    HS = 7
    HVXBIAS = 8
    LVXBIAS = 9
    LVDS = 10
    HEATERX = 11
    XVBIAS = 12
    ADF = 13
    ADX = 14
    ADLN = 15
    UNKNOWN = 16


class ControllerStatus(enum.Flag):
    """Status of the Archon controller."""

    UNKNOWN = 0x1
    IDLE = 0x2
    EXPOSING = 0x4
    READOUT_PENDING = 0x8
    READING = 0x10
    FETCHING = 0x20
    FLUSHING = 0x40
    ERROR = 0x80
    POWERON = 0x100
    POWEROFF = 0x200
    POWERBAD = 0x400

    ACTIVE = EXPOSING | READING | FETCHING | FLUSHING
    ERRORED = ERROR | POWERBAD

    def get_flags(self):
        """Returns the the flags that compose the bit."""

        skip = ["ACTIVE", "ERRORED"]

        return [b for b in ControllerStatus if b & self and b.name not in skip]


class ArchonPower(enum.Enum):
    UNKNOWN = 0
    NOT_CONFIGURED = 1
    OFF = 2
    INTERMEDIATE = 3
    ON = 4
    STANDBY = 5
