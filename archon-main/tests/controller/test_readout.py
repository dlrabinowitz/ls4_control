#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2021-04-06
# @Filename: test_readout.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from unittest.mock import AsyncMock

import pytest

from archon import config
from archon.controller.controller import ArchonController
from archon.controller.maskbits import ControllerStatus
from archon.exceptions import ArchonControllerError


async def test_readout_bad_state(controller: ArchonController):
    controller.update_status(ControllerStatus.EXPOSING)

    with pytest.raises(ArchonControllerError):
        await controller.readout()


@pytest.mark.commands([["FRAME", ["<{cid}WBUF=3 BUF3COMPLETE=1"]]])
async def test_readout(controller: ArchonController, mocker):
    set_param_mock: AsyncMock = mocker.patch.object(
        ArchonController,
        "set_param",
        wraps=controller.set_param,
    )
    controller.update_status([ControllerStatus.IDLE, ControllerStatus.READOUT_PENDING])

    await controller.readout(wait_for=0.01)

    set_param_mock.assert_any_call("ReadOut", 1)
    assert controller.status == ControllerStatus.IDLE | ControllerStatus.POWERON


async def test_readout_no_block(controller: ArchonController):
    controller.update_status([ControllerStatus.IDLE, ControllerStatus.READOUT_PENDING])

    await controller.readout(block=False)

    assert controller.status == ControllerStatus.READING | ControllerStatus.POWERON


async def test_readout_delay(controller: ArchonController, mocker):
    set_param_mock: AsyncMock = mocker.patch.object(
        ArchonController,
        "set_param",
        wraps=controller.set_param,
    )
    controller.update_status([ControllerStatus.IDLE, ControllerStatus.READOUT_PENDING])

    await controller.readout(delay=60, block=False)

    set_param_mock.assert_any_call("WaitCount", 60)
    assert controller.status == ControllerStatus.READING | ControllerStatus.POWERON


@pytest.mark.commands([["FRAME", ["<{cid}WBUF=3 BUF3COMPLETE=0"]]])
async def test_readout_max_wait(controller: ArchonController):
    controller.update_status([ControllerStatus.IDLE, ControllerStatus.READOUT_PENDING])

    config["timeouts"]["readout_max"] = 0.01

    with pytest.raises(ArchonControllerError):
        await controller.readout(wait_for=0.02)


@pytest.mark.commands([["FRAME", ["<{cid}WBUF=3 BUF3COMPLETE=0"]]])
async def test_readout_max_wait_one_loop(controller: ArchonController):
    controller.update_status([ControllerStatus.IDLE, ControllerStatus.READOUT_PENDING])

    config["timeouts"]["readout_max"] = 1

    with pytest.raises(ArchonControllerError):
        await controller.readout(wait_for=0.02)
