#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2021-04-06
# @Filename: flush.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from __future__ import annotations

import click

from clu.command import Command

from archon.controller.controller import ArchonController
from archon.exceptions import ArchonControllerError, ArchonError

from ..tools import error_controller, parallel_controllers
from . import parser


@parser.command()
@click.argument("COUNT", default=1, type=int, required=False)
@parallel_controllers()
async def flush(command: Command, controller: ArchonController, count: int):
    """Flushes controllers."""

    assert command.actor

    try:
        await controller.reset()
        command.actor.expose_data = None
        await controller.flush(count=count)
    except (ArchonControllerError, ArchonError) as err:
        return error_controller(command, controller, f"Failed flushing: {err}")

    return True
