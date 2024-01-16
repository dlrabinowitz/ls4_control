#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2021-01-22
# @Filename: config.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from __future__ import annotations

import os

import click

from clu.command import Command

from archon.controller.controller import ArchonController
from archon.exceptions import ArchonError

from ..tools import check_controller
from . import parser


@parser.group()
def config(*args):
    """Manages the configuration of the device."""

    pass


@config.command()
@click.argument("controller_name", metavar="CONTROLLER")
@click.option(
    "--save",
    "-s",
    is_flag=True,
    help="Saves the configuration to ~/archon_<controller>.acf. "
    "Does not output to console. Overwrites previous files.",
)
async def read(
    command: Command,
    controllers: dict[str, ArchonController],
    controller_name: str,
    save: bool,
):
    """Reads the configuration from the controller."""

    if controller_name not in controllers:
        return command.fail(f"Controller {controller_name!r} does not exist.")

    controller = controllers[controller_name]
    if not check_controller(command, controller):
        return command.fail()

    if save:
        path: str | bool = os.path.expanduser(f"~/archon_{controller.name}.acf")
    else:
        path: str | bool = False

    try:
        _, config = await controller.read_config(save=path)
    except ArchonError as err:
        return command.fail(
            error={
                "controller": controller.name,
                "error": str(err),
            }
        )

    if save is False:
        return command.finish(
            config={
                "controller": controller.name,
                "config": config,
            }
        )

    return command.finish(text=f"Config written to {path!r}")


@config.command()
@click.argument("controller_name", metavar="CONTROLLER")
@click.argument(
    "config_path",
    metavar="PATH",
    type=click.Path(exists=True, dir_okay=False),
)
@click.option(
    "--applyall",
    "-a",
    is_flag=True,
    help="Applies the configuration.",
)
@click.option(
    "--poweron",
    "-p",
    is_flag=True,
    help="Powers the CCD.",
)
async def write(
    command: Command,
    controllers: dict[str, ArchonController],
    controller_name: str,
    config_path: click.Path,
    applyall: bool,
    poweron: bool,
):
    """Writes a configuration file to the controller."""

    if controller_name not in controllers:
        return command.fail(f"Controller {controller_name!r} does not exist.")

    controller = controllers[controller_name]
    if not check_controller(command, controller):
        return command.fail()

    path = str(config_path)

    def notifier(msg):
        command.info(
            text={
                "controller": controller.name,
                "text": msg,
            }
        )

    try:
        await controller.write_config(
            path,
            applyall=applyall,
            poweron=poweron,
            notifier=notifier,
        )
    except ArchonError as err:
        return command.fail(
            error={
                "controller": controller.name,
                "error": str(err),
            }
        )

    return command.finish(text=f"Config file {path!r} successfully loaded.")
