#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2022-04-12
# @Filename: power.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from __future__ import annotations

from typing import TYPE_CHECKING

import click

from archon.controller.maskbits import ArchonPower, ControllerStatus
from archon.exceptions import ArchonError

from ..tools import error_controller, parallel_controllers
from . import parser


if TYPE_CHECKING:
    from archon.actor import ArchonCommandType
    from archon.controller.controller import ArchonController


@parser.command()
@click.argument("MODE", type=click.Choice(["on", "off"]), required=False)
@parallel_controllers()
async def power(
    command: ArchonCommandType,
    controller: ArchonController,
    mode: str | None = None,
):
    """Powers on/off a controller."""

    if mode is None:
        command.info(
            status={
                "controller": controller.name,
                "status": controller.status.value,
                "status_names": [flag.name for flag in controller.status.get_flags()],
            }
        )

        output_func = command.info
        if ControllerStatus.POWERON & controller.status:
            message = "Controller power is on."
        elif ControllerStatus.POWEROFF & controller.status:
            message = "Controller power is off."
        elif ControllerStatus.POWERBAD & controller.status:
            output_func = command.warning
            message = "Controller power is bad"
        else:
            output_func = command.warning
            message = "Controller power is unknown."

        output_func(text={"controller": controller.name, "text": message})
        return True

    try:
        power_status = await controller.power()
    except ArchonError as ee:
        return error_controller(command, controller, str(ee))

    if power_status not in [ArchonPower.ON, ArchonPower.OFF]:
        return error_controller(
            command,
            controller,
            f"Controller reports unsafe power status {power_status.name}",
        )

    if power_status == ArchonPower.OFF and mode == "off":
        command.info(
            text={"controller": controller.name, "text": "Controller is already off."}
        )
        return True

    if power_status == ArchonPower.ON and mode == "on":
        command.info(
            text={"controller": controller.name, "text": "Controller is already on."}
        )
        return True

    if mode == "off":
        await controller.power(False)
    else:
        await controller.power(True)

    if mode == "on":
        await controller.reset()
        if not command.actor.timed_commands.running:
            command.actor.timed_commands.start()

    return True
