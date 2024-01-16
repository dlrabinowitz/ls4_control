#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2023-12-01
# @Filename: recover.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from __future__ import annotations

import pathlib

from typing import TYPE_CHECKING

import astropy.time
import click

from sdsstools import get_sjd

from . import parser


if TYPE_CHECKING:
    from archon.actor.actor import ArchonCommandType
    from archon.controller.controller import ArchonController


@parser.command()
@click.argument("PATH", type=str, required=False)
@click.option(
    "--write-checksum",
    is_flag=True,
    help="Adds the checksum of the recovered files to the checksum file.",
)
@click.option(
    "--keep-lock",
    is_flag=True,
    help="Do not remove the lockfile.",
)
async def recover(
    command: ArchonCommandType,
    controllers: dict[str, ArchonController],
    path: str | None = None,
    write_checksum: bool = False,
    keep_lock: bool = False,
):
    """Recovers a failed exposure.

    PATH is either the path to the lockfile of the missing exposure or a directory
    for which all available lockfiles will be recovered. If PATH is not provided the
    default path will be used.

    """

    config = command.actor.config

    if path is None:
        now = astropy.time.Time.now()
        mjd = get_sjd() if config.get("files.use_sjd", False) else int(now.mjd)
        data_dir = pathlib.Path(config.get("files.data_dir", "/data"))

        recovery_path = data_dir / str(mjd)

    else:
        recovery_path = pathlib.Path(path)

    if not recovery_path.exists():
        return command.fail(f"Path {recovery_path!s} does not exist. Recovery failed.")

    with command.actor.exposure_recovery.set_command(command):
        recovered = await command.actor.exposure_recovery.recover(
            config["controllers"],
            path=recovery_path,
            write_checksum=write_checksum,
            checksum_mode=config["checksum.mode"],
            checksum_file=config["checksum.file"],
            delete_lock=not keep_lock,
        )

    if len(recovered) == 0:
        command.info("No exposures were recovered.")

    command.finish(filenames=[str(fn) for fn in recovered])
