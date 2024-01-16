#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2021-01-21
# @Filename: status.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from __future__ import annotations

import click

from clu.command import Command

import archon.actor
from archon.controller.controller import ArchonController
from archon.exceptions import ArchonError

from ..tools import error_controller, parallel_controllers
from . import parser


@parser.command()
@click.option("-s", "--simple", is_flag=True, help="Only show status bits.")
@click.option("-d", "--debug", is_flag=True, help="Uses debug status in outputs..")
@parallel_controllers()
async def status(
    command: Command[archon.actor.actor.ArchonActor],
    controller: ArchonController,
    simple: bool = False,
    debug: bool = False,
):
    """Reports the status of the controller."""

    try:
        status = await controller.get_device_status()
    except ArchonError as ee:
        return error_controller(command, controller, str(ee))

    if debug:
        write_func = command.debug
    else:
        write_func = command.info

    if simple:
        write_func(
            status={
                "controller": controller.name,
                "status": controller.status.value,
                "status_names": [flag.name for flag in controller.status.get_flags()],
            }
        )
        return True

    write_func(
        status={
            "controller": controller.name,
            "status": controller.status.value,
            "status_names": [flag.name for flag in controller.status.get_flags()],
            **status,
        }
    )

    return True
