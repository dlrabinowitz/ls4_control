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

    NOSTATUS = 0x0
    UNKNOWN = 0x1
    IDLE = 0x2
    EXPOSING = 0x4
    READOUT_PENDING = 0x8
    READING = 0x10
    FETCHING = 0x20
    FLUSHING = 0x40
    ERASING = 0x80
    PURGING = 0x100
    AUTOCLEAR = 0x200
    AUTOFLUSH = 0x400
    POWERON = 0x800
    POWEROFF = 0x1000
    POWERBAD = 0x2000
    FETCH_PENDING = 0x4000
    ERROR = 0x8000

    ACTIVE = EXPOSING | READING | FETCHING | FLUSHING | ERASING | PURGING 
    ERRORED = ERROR | POWERBAD

    def get_flags(self):
        """Returns the the flags that compose the bit."""

        skip = ["ACTIVE", "ERRORED"]

        return [b for b in ControllerStatus if b & self and b.name not in skip]

    @property
    def status_dict(self):

        """ return a dictionary with values 0 of 1 for each bit name
            if the corresponsing but is 0 or 1 in t the specified
            status value
        """

        bit_names=["NOSTATUS","UNKNOWN","IDLE","EXPOSING","READOUT_PENDING","READING",\
                   "FETCHING","FLUSHING","ERASING", "PURGING",\
                   "AUTOCLEAR","AUTOFLUSH", "POWERON","POWEROFF","POWERBAD","FETCH_PENDING",\
                   "ERROR","ACTIVE","ERRORED"]

        bit_values=[self.NOSTATUS,self.UNKNOWN,self.IDLE,self.EXPOSING,\
                   self.READOUT_PENDING,self.READING,\
                   self.FETCHING,self.FLUSHING,self.ERASING, self.PURGING,\
                   self.AUTOCLEAR, self.AUTOFLUSH,self.POWERON,self.POWEROFF,self.POWERBAD,\
                   self.FETCH_PENDING,self.ERROR,self.ACTIVE,self.ERRORED]


        status_val = self

        index = 0
        result={}
        for index in range(0,len(bit_names)):
            b= bit_values[index]
            if status_val & b:
                val = 1
            else:
                val = 0
            key="BIT_"+bit_names[index]
            result[key]=val
            index += 1

        return result

class ArchonPower(enum.Enum):
    UNKNOWN = 0
    NOT_CONFIGURED = 1
    OFF = 2
    INTERMEDIATE = 3
    ON = 4
    STANDBY = 5
