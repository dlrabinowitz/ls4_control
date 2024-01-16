#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2021-01-21
# @Filename: talk.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from __future__ import annotations

import click

from clu.command import Command

from archon.controller.controller import ArchonController

from ..tools import parallel_controllers
from . import parser


@parser.command()
@click.argument("archon_command", metavar="COMMAND", type=str)
@parallel_controllers()
async def talk(
    command: Command,
    controller: ArchonController,
    archon_command: str,
):
    """Sends a command to the controller."""

    cmd = controller.send_command(archon_command)
    await cmd

    async for reply in cmd.get_replies():
        # Need to decode so that's serializable.
        raw = reply.raw_reply.decode().strip()
        if reply.type == "?":
            output_func = command.error
        else:
            output_func = command.info

        output_func(
            message={
                "raw_reply": {
                    "controller": controller.name,
                    "command": cmd.raw,
                    "response": raw,
                }
            }
        )

    return True
