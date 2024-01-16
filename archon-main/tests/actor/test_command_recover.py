#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2023-12-01
# @Filename: test_command_recover.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from __future__ import annotations

import pathlib

from typing import TYPE_CHECKING

from pytest_mock import MockerFixture

from sdsstools import get_sjd


if TYPE_CHECKING:
    from archon.actor.actor import ArchonActor


async def test_recover(actor: ArchonActor, recovery_lockfile: pathlib.Path):
    command = await actor.invoke_mock_command(f"recover {recovery_lockfile!s}")
    await command

    fits_file = recovery_lockfile.parent / recovery_lockfile.name.replace(".lock", "")
    assert fits_file.exists()

    assert command.status.did_succeed
    assert len(command.replies[-1].message["filenames"]) == 1


async def test_recover_no_path(actor: ArchonActor, mocker: MockerFixture):
    recover_mock = mocker.patch.object(actor.exposure_recovery, "recover")

    command = await actor.invoke_mock_command("recover")
    await command

    assert command.status.did_succeed
    assert len(command.replies[-1].message["filenames"]) == 0

    sjd = get_sjd()
    recover_mock.assert_called_once_with(
        mocker.ANY,
        path=pathlib.Path(f"/var/tmp/{sjd}"),
        checksum_file=None,
        checksum_mode="md5",
        delete_lock=True,
        write_checksum=False,
    )


async def test_recover_bad_path(actor: ArchonActor):
    command = await actor.invoke_mock_command("recover /bad/path/to/file.lock")
    await command

    assert command.status.did_fail
