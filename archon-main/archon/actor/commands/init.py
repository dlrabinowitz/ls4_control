#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2021-01-26
# @Filename: init.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from __future__ import annotations

import asyncio
import os

from typing import TYPE_CHECKING

import click

from archon.controller.command import ArchonCommand
from archon.exceptions import ArchonError

from ..tools import error_controller, parallel_controllers
from . import parser


if TYPE_CHECKING:
    from archon.actor import ArchonCommandType
    from archon.controller.controller import ArchonController


def _output(
    command: ArchonCommandType,
    controller: ArchonController,
    text: str,
    message_code="d",
):
    command.write(
        message_code=message_code,
        text=dict(
            controller=controller.name,
            text=text,
        ),
    )


@parser.command()
@click.argument("ACF-FILE", type=str, required=False)
@click.option(
    "--applymod",
    "-a",
    type=str,
    multiple=True,
    help="Apply command to send. Multiple instances are allowed. "
    "If none is provided, APPLYALL will be sent, followed by a power cycle.",
)
@click.option("--power/--no-power", default=True, help="Power the array after init.")
@parallel_controllers()
async def init(
    command: ArchonCommandType,
    controller: ArchonController,
    acf_file: str | None = None,
    applymod: list[str] = [],
    power: bool = True,
):
    """Initialises a controller."""

    applyall = True if len(applymod) == 0 else False

    assert command.actor

    # Load config, apply all, LOADPARAMS, and LOADTIMING, but no power up.
    archon_etc = os.path.join(os.path.dirname(__file__), "../../etc")

    if acf_file is None:
        if isinstance(command.actor.config["archon"]["acf_file"], dict):
            if controller.name not in command.actor.config["archon"]["acf_file"]:
                return error_controller(
                    command,
                    controller,
                    "No ACF file defined for this controller.",
                )
            acf_file = command.actor.config["archon"]["acf_file"][controller.name]
        else:
            acf_file = command.actor.config["archon"]["acf_file"]

    if acf_file is None:
        return error_controller(command, controller, "Invalid ACF file.")

    acf_file = acf_file.format(archon_etc=archon_etc)

    if not os.path.isabs(acf_file):
        if command.actor.config_file_path is not None:
            config_dirname = os.path.dirname(command.actor.config_file_path)
            acf_file = os.path.join(config_dirname, acf_file)
        else:
            return error_controller(
                command,
                controller,
                "The actor does not know the path of the configuration file. "
                "ACF file path must be absolute.",
            )

    if not os.path.exists(acf_file):
        return error_controller(command, controller, f"Cannot find file {acf_file}")

    _output(command, controller, f"Loading and applying ACF file {acf_file}", "i")

    # Stop timed commands since they may fail while writing data or power is off
    await command.actor.timed_commands.stop()

    # Read configuration overrides.
    overrides = {}
    if "acf_overrides" in command.actor.config["archon"]:
        overrides_cfg = command.actor.config["archon"]["acf_overrides"]
        overrides = overrides_cfg.get("global", {}).copy()
        if controller.name in overrides_cfg:
            overrides.update(overrides_cfg[controller.name])

    try:
        data = open(acf_file).read()
        await controller.write_config(
            data,
            applyall=applyall,
            applymods=applymod,
            poweron=False,
            overrides=overrides,
        )
    except ArchonError as err:
        return error_controller(command, controller, str(err))

    # Set parameters
    _output(command, controller, "Setting initial parameters")
    initial_params = {"Exposures": 0, "ReadOut": 0, "DoFlush": 0}
    for param, value in initial_params.items():
        try:
            await controller.set_param(param, value)
        except ArchonError as err:
            return error_controller(command, controller, str(err))

    # Unlock all buffers
    _output(command, controller, "Unlocking buffers")
    acmd: ArchonCommand = await controller.send_command("LOCK0", timeout=5)
    if not acmd.succeeded():
        return error_controller(
            command,
            controller,
            f"Failed while unlocking frame buffers ({acmd.status.name})",
        )

    # Power on
    if applyall and power:
        _output(command, controller, "Powering on")
        acmd: ArchonCommand = await controller.send_command("POWERON", timeout=10)
        if not acmd.succeeded():
            return error_controller(
                command,
                controller,
                f"Failed while powering on ({acmd.status.name})",
            )

        # Sometimes if we reset immediately after POWERON the power
        # is in intermediate state. Let's give it a few seconds.
        await asyncio.sleep(3)

    await controller.reset()
    if not command.actor.timed_commands.running:
        command.actor.timed_commands.start()

    return True
