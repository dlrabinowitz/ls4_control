#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2021-01-21
# @Filename: system.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from __future__ import annotations

from clu.command import Command

from archon.controller.controller import ArchonController
from archon.exceptions import ArchonError

from ..tools import error_controller, parallel_controllers
from . import parser


@parser.command()
@parallel_controllers()
async def system(command: Command, controller: ArchonController):
    """Reports the status of the controller backplane."""

    try:
        system = await controller.get_system()
    except ArchonError as ee:
        return error_controller(command, controller, str(ee))

    command.info(
        system={
            "controller": controller.name,
            **system,
        }
    )

    return True
