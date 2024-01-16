#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2021-03-07
# @Filename: reconnect.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

import asyncio

import click

from clu.command import Command

from archon.actor.commands import parser
from archon.actor.tools import parallel_controllers
from archon.controller.controller import ArchonController


@parser.command()
@click.option("--timeout", "-t", type=float, help="Time to wait while (dis)connecting.")
@parallel_controllers(check=False)
async def reconnect(command: Command, controller: ArchonController, timeout: float):
    """Restarts the socket connection to the controller(s)."""

    assert command.actor

    name = controller.name
    connect_timeout = timeout or command.actor.config["timeouts"]["controller_connect"]

    if controller.is_connected():
        try:
            await asyncio.wait_for(controller.stop(), timeout=timeout or 3)
        except BaseException as err:
            command.warning(
                text=f"Failed disconnecting from {name!r} with "
                f"error {err}. Will try to reconnect."
            )

    try:
        await asyncio.wait_for(controller.start(), timeout=connect_timeout)
    except asyncio.TimeoutError:
        command.error(error=f"Timed-out while reconnecting to controller {name!r}.")
        return False
    except BaseException as err:
        command.error(
            error=f"Unexpected error while connecting to controller {name!r}: {err}"
        )
        return False

    return True
