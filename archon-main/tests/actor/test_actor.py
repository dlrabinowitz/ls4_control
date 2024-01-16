#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2021-09-03
# @Filename: test_actor.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from __future__ import annotations

import pathlib

from typing import TYPE_CHECKING

import pytest

from archon.actor import ArchonActor
from archon.actor.recovery import ExposureRecovery


if TYPE_CHECKING:
    from archon.actor.delegate import FetchDataDict


async def test_actor(actor: ArchonActor):
    assert actor
    assert len(actor.controllers) == 1
    assert actor.controllers["sp1"].is_connected()


async def test_ping(actor):
    command = await actor.invoke_mock_command("ping")
    await command

    assert command.status.did_succeed
    assert len(command.replies) == 2
    assert command.replies[1].message["text"] == "Pong."


async def test_actor_no_config():
    with pytest.raises(RuntimeError):
        ArchonActor.from_config(None)


async def test_actor_recover_exposures(
    actor: ArchonActor,
    exposure_recovery: ExposureRecovery,
    fetch_data: FetchDataDict,
):
    exposure_recovery.update(fetch_data)

    filename = pathlib.Path(fetch_data["filename"])

    actor.config["files"]["data_dir"] = filename.parents[1]
    recovered = await actor._recover_exposures()

    assert filename.exists()
    assert recovered is not None and len(recovered) == 1


async def test_actor_recover_exposures_invalid_path(actor: ArchonActor):
    actor.config["files"]["data_dir"] = "/bad/path"
    recovered = await actor._recover_exposures()
    assert recovered is None
