#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2021-01-30
# @Filename: test_expose.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from unittest.mock import AsyncMock

import pytest

from archon.controller.controller import ArchonController
from archon.controller.maskbits import ControllerStatus
from archon.exceptions import ArchonControllerError


@pytest.mark.commands([["FRAME", ["<{cid}WBUF=3 BUF3COMPLETE=0"]]])
async def test_expose(controller: ArchonController, mocker):
    set_param_mock: AsyncMock = mocker.patch.object(
        ArchonController,
        "set_param",
        wraps=controller.set_param,
    )
    task = await controller.expose(0.01)
    set_param_mock.assert_any_call("Exposures", 1)
    set_param_mock.assert_any_call("IntCS", 1)

    assert controller.status & ControllerStatus.EXPOSING
    assert controller.status & ControllerStatus.READOUT_PENDING

    await task
    assert controller.status == ControllerStatus.READING | ControllerStatus.POWERON


async def test_expose_not_idle(controller: ArchonController):
    controller.update_status(ControllerStatus.READOUT_PENDING)
    with pytest.raises(ArchonControllerError):
        await controller.expose(2)


@pytest.mark.commands([["FRAME", ["<{cid}WBUF=3 BUF3COMPLETE=1"]]])
async def test_expose_fails_reading(controller: ArchonController, mocker):
    task = await controller.expose(0.01)

    with pytest.raises(ArchonControllerError):
        await task


async def test_expose_no_readout(controller: ArchonController, mocker):
    task = await controller.expose(0.01, readout=False)

    await task
    assert controller.status & ControllerStatus.READOUT_PENDING


async def test_abort(controller: ArchonController, mocker):
    task = await controller.expose(0.01)

    await controller.abort(readout=True)
    await task

    assert controller.status & ControllerStatus.READING


async def test_abort_no_readout(controller: ArchonController, mocker):
    task = await controller.expose(0.01)

    await controller.abort(readout=False)
    await task

    assert controller.status & ControllerStatus.IDLE
    assert controller.status & ControllerStatus.READOUT_PENDING


async def test_abort_no_exposing(controller: ArchonController):
    controller.update_status(ControllerStatus.IDLE)

    with pytest.raises(ArchonControllerError):
        await controller.abort()
