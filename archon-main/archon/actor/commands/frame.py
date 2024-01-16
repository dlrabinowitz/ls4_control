#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2021-01-24
# @Filename: frame.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from __future__ import annotations

import os
import re
from glob import glob

import astropy.io.fits
import click

from clu.command import Command

from archon.actor.commands import parser
from archon.actor.tools import check_controller
from archon.controller.controller import ArchonController
from archon.exceptions import ArchonError


@parser.group()
def frame(*args):
    """Interacts with the controller buffer frame."""

    pass


@frame.command()
@click.argument("controller_name", metavar="CONTROLLER")
async def status(
    command: Command,
    controllers: dict[str, ArchonController],
    controller_name: str,
):
    """Reads the frame status."""

    if controller_name not in controllers:
        return command.fail(f"Controller {controller_name!r} does not exist.")

    controller = controllers[controller_name]
    if not check_controller(command, controller):
        return command.fail()

    try:
        frame = await controller.get_frame()
    except ArchonError as err:
        return command.fail(
            error={
                "controller": controller.name,
                "error": err,
            }
        )

    return command.finish(
        frame={
            "controller": controller.name,
            **frame,
        }
    )


@frame.command()
@click.argument("controller_name", metavar="CONTROLLER")
@click.option(
    "-b",
    "--buffer",
    type=click.Choice(["-1", "1", "2", "3"]),
    default="-1",
    help="The frame buffer to read. Defaults to -1 (last written buffer).",
)
@click.option(
    "--file",
    "-f",
    type=click.Path(),
    default=None,
    help="Path where to write the file. Will be overwritten. "
    "Defaults to ~/archon_<controller>_NNNN.fits",
)
async def fetch(
    command: Command,
    controllers: dict[str, ArchonController],
    controller_name: str,
    buffer: str,
    file,
):  # pragma: no cover
    """Low-level command to fetch a buffer and write it to disk."""

    if controller_name not in controllers:
        return command.fail(f"Controller {controller_name!r} does not exist.")

    controller = controllers[controller_name]
    if not check_controller(command, controller):
        return command.fail()

    buffer_no = int(buffer)

    if file is None:
        # Save to ~/archon_<controller_name>_NNNN.fits. Find the highest file with that
        # format and increase the counter.
        pattern = os.path.expanduser(
            f"~/archon_{controller.name}_[0-9][0-9][0-9][0-9].fits"
        )
        existing = glob(pattern)
        if len(existing) == 0:
            nfile = 1
        else:
            last = sorted(existing)[-1]
            search = re.search(r"([0-9]{4})\.fits$", last)
            assert search is not None
            nfile = int(search[1]) + 1
        path = os.path.expanduser(f"~/archon_{controller.name}_{nfile:04d}.fits")
    else:
        path: str = os.path.relpath(str(file))
        dirname = os.path.dirname(path)
        if not os.path.exists(dirname):
            return command.fail(
                error="Parent of file does not exists or file is badly formatted."
            )

    def notifier(msg):
        command.info(
            text={
                "controller": controller.name,
                "text": msg,
            }
        )

    try:
        array = await controller.fetch(buffer_no, notifier=notifier)
    except BaseException as err:
        return command.fail(
            text={
                "controller": controller.name,
                "text": f"Failed fetching data: {str(err)}",
            }
        )

    # Create a simple HDU list with the data.
    hdu = astropy.io.fits.PrimaryHDU(data=array)
    hdulist = astropy.io.fits.HDUList([hdu])
    hdulist.writeto(path, overwrite=True)

    return command.finish(f"File saved to {path}")
