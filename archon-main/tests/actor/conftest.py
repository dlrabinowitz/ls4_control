#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2021-09-03
# @Filename: conftest.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from __future__ import annotations

import os
import pathlib

from typing import TYPE_CHECKING, Generator

import numpy
import pytest
import pytest_asyncio
from pytest_mock import MockFixture

import clu.testing
from clu.actor import AMQPBaseActor
from sdsstools import get_sjd, merge_config, read_yaml_file

from archon import config
from archon.actor import ArchonActor
from archon.actor.recovery import ExposureRecovery
from archon.controller.controller import ArchonController
from archon.controller.maskbits import ControllerStatus


if TYPE_CHECKING:
    from archon.actor.delegate import FetchDataDict


@pytest.fixture()
def test_config():
    extra = read_yaml_file(os.path.join(os.path.dirname(__file__), "config.yaml"))
    yield merge_config(extra, config)


@pytest_asyncio.fixture()
async def actor(test_config: dict, controller: ArchonController, mocker):
    # We need to call the actor .start() method to force it to create the
    # controllers and to start the tasks, but we don't want to run .start()
    # on the actor.
    mocker.patch.object(AMQPBaseActor, "start")

    test_config["controllers"]["sp1"]["host"] = controller.host
    test_config["controllers"]["sp1"]["port"] = controller.port

    _actor = ArchonActor.from_config(test_config)
    _actor.config_file_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    await _actor.start()

    # Replace controller since the one after .start() has only a partial ACF.
    _actor.controllers["sp1"] = controller

    _actor = await clu.testing.setup_test_actor(_actor)  # type: ignore

    yield _actor

    _actor.mock_replies.clear()
    await _actor.stop()


@pytest.fixture()
def delegate(actor: ArchonActor, monkeypatch, tmp_path: pathlib.Path, mocker):
    def reset_status(**kwargs):
        actor.controllers["sp1"].update_status(ControllerStatus.IDLE)
        actor.controllers["sp1"].update_status(ControllerStatus.READOUT_PENDING, "off")

    mocker.patch.object(
        actor.controllers["sp1"],
        "readout",
        return_value=True,
        side_effect=reset_status,
    )

    # For framemode=top
    mocker.patch.object(
        actor.controllers["sp1"],
        "fetch",
        return_value=(numpy.ones((1000, 3000)), 1),
    )

    assert actor.model

    mocker.patch.object(
        actor.controllers["sp1"],
        "get_device_status",
        return_value={
            "controller": "sp1",
            "mod2/tempa": -110,
            "mod2/tempb": -110,
            "mod2/tempc": -110,
            "mod12/tempa": -110,
            "mod12/tempb": -110,
            "mod12/tempc": -110,
            "power": 4,
            "powergood": 1,
        },
    )

    files_data_dir = tmp_path / "archon"

    monkeypatch.setitem(actor.config["files"], "data_dir", str(files_data_dir))

    yield actor.exposure_delegate


@pytest.fixture()
def exposure_recovery(controller: ArchonController, mocker: MockFixture):
    mocker.patch.object(
        controller,
        "fetch",
        return_value=numpy.ones((1000, 3000)),
    )

    _exposure_recovery = ExposureRecovery({"sp1": controller})

    yield _exposure_recovery


@pytest.fixture()
def controller_info(test_config: dict) -> Generator[dict, None, None]:
    yield test_config["controllers"]


@pytest.fixture()
def fetch_data(tmp_path: pathlib.Path):
    sjd = get_sjd()

    _fetch_data: FetchDataDict = {
        "buffer": 1,
        "ccd": "r1",
        "controller": "sp1",
        "exposure_no": 1,
        "filename": str(tmp_path / str(sjd) / "test.fits"),
        "data": numpy.array([]),
        "header": {
            "KEY1": ["value", "A comment"],
            "FILENAME": ["", ""],
            "EXPOSURE": ["", ""],
        },
    }

    yield _fetch_data


@pytest.fixture()
def recovery_lockfile(fetch_data: FetchDataDict, exposure_recovery: ExposureRecovery):
    exposure_recovery.update(fetch_data)
    lockfile = pathlib.Path(fetch_data["filename"] + ".lock")

    yield lockfile

    lockfile.unlink(missing_ok=True)
