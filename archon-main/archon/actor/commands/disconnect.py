#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2022-04-26
# @Filename: disconnect.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from __future__ import annotations

from typing import TYPE_CHECKING

from archon.actor.commands import parser
from archon.actor.tools import parallel_controllers


if TYPE_CHECKING:
    from archon.actor import ArchonCommandType
    from archon.controller.controller import ArchonController


@parser.command()
@parallel_controllers(check=False)
async def disconnect(command: ArchonCommandType, controller: ArchonController):
    """Disconnects a controller."""

    assert command.actor

    name = controller.name

    if controller.is_connected():
        try:
            await controller.stop()
        except BaseException as err:
            command.warning(text=f"Failed disconnecting from {name} with error {err}.")
            return False
    else:
        command.warning(f"Controller {name} is already disconnected.")

    return True
