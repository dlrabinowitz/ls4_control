#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2021-01-27
# @Filename: expose.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from __future__ import annotations

import asyncio
import json

from typing import Dict

import click

from clu.command import Command

import archon.actor
from archon.controller.controller import ArchonController
from archon.controller.maskbits import ControllerStatus
from archon.exceptions import ArchonError

from ..tools import check_controller, controller
from . import parser


__all__ = ["expose", "read", "abort", "wait_until_idle"]


@parser.command()
@controller
@click.argument(
    "EXPOSURE-TIME",
    type=float,
    nargs=1,
    required=False,
)
@click.option(
    "--window-mode",
    type=str,
    help="Exposure window profile.",
)
@click.option(
    "--bias",
    "flavour",
    flag_value="bias",
    default=False,
    show_default=True,
    help="Take a bias.",
)
@click.option(
    "--dark",
    "flavour",
    flag_value="dark",
    default=False,
    help="Take a dark.",
)
@click.option(
    "--flat",
    "flavour",
    flag_value="flat",
    default=False,
    help="Take a flat.",
)
@click.option(
    "--arc",
    "flavour",
    flag_value="arc",
    default=False,
    help="Take an arc.",
)
@click.option(
    "--object",
    "flavour",
    flag_value="object",
    default=True,
    help="Take an object frame.",
)
@click.option(
    "--readout/--no-readout",
    " /-R",
    default=True,
    help="Whether to read out the frame.",
)
@click.option(
    "--async-readout",
    default=False,
    is_flag=True,
    help="When set, readout will be initiated but the command returns "
    "immediately as readout begins. If multiple exposures are commanded only "
    "the last one will be read out asynchronously.",
)
@click.option(
    "--header",
    type=str,
    default="{}",
    help="JSON string with additional header keyword-value pairs. Avoid using spaces.",
)
@click.option(
    "-d",
    "--delay-readout",
    type=int,
    default=0,
    help="Slow down the readout by this many seconds.",
)
@click.option(
    "-n",
    "--count",
    type=int,
    default=1,
    help="Number of images to take.",
)
@click.option(
    "--no-write",
    "-W",
    is_flag=True,
    help="Do not write image after reading.",
)
@click.option(
    "--no-shutter",
    is_flag=True,
    help="Do not trigger the shutter.",
)
@click.option(
    "--with-dark",
    is_flag=True,
    help="Take a matching dark exposure.",
)
@click.option(
    "-s",
    "--seqno",
    type=int,
    help="Sequence number for the expossure.",
)
async def expose(
    command: Command[archon.actor.actor.ArchonActor],
    controllers: dict[str, ArchonController],
    exposure_time: float | None = None,
    window_mode: str | None = None,
    controller: str | None = None,
    flavour: str = "object",
    readout: bool = True,
    async_readout: bool = False,
    header: str = "{}",
    delay_readout: int = 0,
    count: int = 1,
    no_shutter: bool = False,
    with_dark: bool = False,
    no_write: bool = False,
    seqno: int | None = None,
):
    """Exposes the cameras."""

    assert command.actor

    selected_controllers: list[ArchonController]

    if with_dark and not readout:
        return command.fail("--with-dark cannot be used with --no-readout.")

    if not controller:
        selected_controllers = list(controllers.values())
    else:
        if controller not in controllers:
            return command.fail(error=f"Controller {controller!r} not found.")
        selected_controllers = [controllers[controller]]

    if not all([check_controller(command, c) for c in selected_controllers]):
        return command.fail()

    delegate = command.actor.exposure_delegate
    if delegate is None:
        return command.fail(error="Cannot find expose delegate.")

    extra_header = json.loads(header)
    if not isinstance(extra_header, dict):
        command.warning("Ignoring invalid header. Header must be a JSON dict string.")
        extra_header = {}

    if count > 1 and readout is False:
        return command.fail(error="--count > 1 requires readout.")

    # Wait for any ongoing recovery to finish.
    if not command.actor.exposure_recovery.locker.is_set():
        command.warning("Waiting for image recovery to finish.")
        await command.actor.exposure_recovery.locker.wait()

    for nexp in range(1, count + 1):
        flavours = [flavour, "dark"] if with_dark else [flavour]
        for nf, this_flavour in enumerate(flavours):
            delegate.use_shutter = not no_shutter
            exposure_result = await delegate.expose(
                command,
                selected_controllers,
                flavour=this_flavour,
                exposure_time=exposure_time,
                readout=False,
                window_mode=window_mode,
                write=not no_write,
                seqno=seqno,
            )

            if not exposure_result:
                # expose will fail the command.
                return

            if readout is True:
                is_async = async_readout and nexp == count and nf == len(flavours) - 1

                # Finish here so that readout receives a done command.
                if is_async:
                    command.finish("Returning while readout is ongoing.")

                readout_task = asyncio.create_task(
                    delegate.readout(
                        command,
                        extra_header=extra_header,
                        delay_readout=delay_readout,
                    )
                )

                if is_async:
                    return

                readout_result = await readout_task

                if not readout_result:
                    return

    return command.finish()


@parser.command()
@click.option(
    "--header",
    type=str,
    default="{}",
    help="JSON string with additional header keyword-value pairs. Avoid using spaces.",
)
@click.option(
    "-d",
    "--delay-readout",
    type=int,
    default=0,
    help="Slow down the readout by this many seconds.",
)
async def read(
    command: Command[archon.actor.actor.ArchonActor],
    controllers: Dict[str, ArchonController],
    header: str,
    delay_readout: int,
):
    """Finishes the ongoing exposure."""

    assert command.actor

    delegate = command.actor.exposure_delegate
    if delegate is None:
        return command.fail(error="Cannot find expose delegate.")

    extra_header = json.loads(header)

    # Wait for any ongoing recovery to finish.
    if not command.actor.exposure_recovery.locker.is_set():
        command.warning("Waiting for image recovery to finish.")
        await command.actor.exposure_recovery.locker.wait()

    result = await delegate.readout(
        command,
        extra_header=extra_header,
        delay_readout=delay_readout,
    )

    if result is True:
        return command.finish()
    else:
        return


@parser.command()
@click.option("--flush", is_flag=True, help="Flush the device after aborting.")
@click.option("--force", is_flag=True, help="Forces abort.")
@click.option("--all", "all_", is_flag=True, help="Aborts all the controllers.")
async def abort(
    command: Command[archon.actor.actor.ArchonActor],
    controllers: dict[str, ArchonController],
    flush: bool,
    force: bool,
    all_: bool,
):
    """Aborts the exposure."""

    assert command.actor

    if all_:
        force = True

    expose_data = command.actor.exposure_delegate.expose_data

    if expose_data is None:
        if force:
            command.warning(error="No exposure found.")
        else:
            command.actor.exposure_delegate.reset()
            return command.fail(error="No exposure found.")

    scontr: list[ArchonController]
    if all_ or not expose_data:
        scontr = list(controllers.values())
    else:
        scontr = expose_data.controllers

    command.debug(text="Aborting exposures")
    try:
        await asyncio.gather(*[contr.abort(readout=False) for contr in scontr])
    except ArchonError as err:
        return command.fail(error=f"Failed aborting exposures: {err}")
    finally:
        command.actor.exposure_delegate.reset()

    if flush:
        command.debug(text="Flushing devices")
        try:
            await asyncio.gather(*[contr.flush() for contr in scontr])
        except ArchonError as err:
            return command.fail(error=f"Failed flushing devices: {err}")

    return command.finish()


@parser.command()
@click.option(
    "--allow-errored",
    is_flag=True,
    help="Returns even if the spectrograph status is ERROR as long as it is IDLE.",
)
async def wait_until_idle(
    command: Command[archon.actor.actor.ArchonActor],
    controllers: dict[str, ArchonController],
    allow_errored: bool = False,
):
    """Wait until the spectrograph status is IDLE and there is no READOUT_PENDING."""

    while True:
        await asyncio.sleep(1)

        statuses = [controller.status for controller in controllers.values()]

        is_idle = [status & ControllerStatus.IDLE for status in statuses]
        is_pending = [status & ControllerStatus.READOUT_PENDING for status in statuses]
        is_errored = [status & ControllerStatus.ERRORED for status in statuses]

        if not all(is_idle):
            continue

        if command.actor.exposure_delegate.is_writing:
            continue

        if allow_errored:
            if any(is_errored):
                command.warning("Some controllers are ERRORED.")
            break
        else:
            if any(is_pending):
                continue
            break

    return command.finish("All controllers are IDLE.")
