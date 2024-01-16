#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2021-05-02
# @Filename: reset.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from __future__ import annotations

from clu.command import Command

from archon.controller.controller import ArchonController
from archon.exceptions import ArchonControllerError, ArchonError

from ..tools import error_controller, parallel_controllers
from . import parser


@parser.command()
@parallel_controllers()
async def reset(command: Command, controller: ArchonController):
    """Resets the controllers and discards ongoing exposures."""

    assert command.actor

    try:
        await controller.reset()
        command.actor.expose_data = None
    except (ArchonControllerError, ArchonError) as err:
        return error_controller(command, controller, f"Failed resetting: {err}")
    finally:
        command.actor.exposure_delegate.reset()

    return True
