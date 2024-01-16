#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2021-01-20
# @Filename: test_controller.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

import asyncio

import pytest

from archon.controller.controller import ArchonController
from archon.controller.maskbits import ControllerStatus
from archon.exceptions import (
    ArchonControllerError,
    ArchonControllerWarning,
    ArchonError,
)


@pytest.mark.commands([["PING", ["<{cid}PONG"]]])
async def test_controller(controller: ArchonController):
    assert controller.host == "localhost"
    command = controller.send_command("ping")
    await command
    assert command.status == command.status.DONE
    assert command.replies[0].reply == "PONG"
    assert str(command.replies[0]) == "PONG"


@pytest.mark.commands([["PING", [b"<{cid}:12345"]]])
async def test_controller_binary_reply(controller: ArchonController):
    command = controller.send_command("ping")
    await command
    assert command.status == command.status.DONE
    assert len(command.replies) == 1
    assert len(command.replies[0].reply) == 1024
    assert command.replies[0].reply.strip() == b"12345"
    with pytest.raises(ArchonError):
        str(command.replies[0])


@pytest.mark.commands([["PING", ["?{cid}"]]])
async def test_controller_error(controller: ArchonController):
    command = controller.send_command("ping")
    await command
    assert command.status == command.status.FAILED
    assert command.replies[0].type == "?"


@pytest.mark.commands([["PING", ["<?!PONG"]]])
async def test_controller_command_not_running(controller: ArchonController):
    with pytest.warns(ArchonControllerWarning):
        controller.send_command("ping")
        await asyncio.sleep(0.01)


@pytest.mark.xfail
@pytest.mark.commands([["PING", ["<02PONG"]]])
async def test_controller_bad_reply(controller: ArchonController):
    with pytest.warns(ArchonControllerWarning):
        controller.send_command("ping", command_id=1)
        await asyncio.sleep(0.01)


@pytest.mark.commands([])
@pytest.mark.parametrize("command_id", [-1, 256])
async def test_controller_bad_command_id(controller: ArchonController, command_id: int):
    with pytest.raises(ArchonControllerError):
        controller.send_command("PING", command_id=command_id)


@pytest.mark.commands([["FASTLOADPARAM", ["<{cid}"]]])
async def test_controller_set_param(controller: ArchonController):
    cmd = await controller.set_param("Lines", 1)
    assert cmd is not None
    assert cmd.succeeded()


@pytest.mark.commands([["FASTLOADPARAM", ["?{cid}"]]])
async def test_controller_set_param_fails(controller: ArchonController):
    with pytest.raises(ArchonControllerError):
        await controller.set_param("Lines", 1)


@pytest.mark.commands([["RESETTIMING", ["<{cid}"]]])
async def test_controller_reset(controller: ArchonController):
    await controller.reset()


async def test_yield_status(controller: ArchonController):
    async def set_status():
        controller.update_status(ControllerStatus.IDLE)
        await asyncio.sleep(0.01)
        controller.update_status(ControllerStatus.EXPOSING)

    asyncio.create_task(set_status())

    status = None
    async for status in controller.yield_status():
        if status == ControllerStatus.EXPOSING | ControllerStatus.POWERON:
            break

    assert status and status == ControllerStatus.EXPOSING | ControllerStatus.POWERON


async def test_start_with_reset(controller: ArchonController):
    await controller.stop()
    await controller.start(reset=True)

    assert controller.status & ControllerStatus.IDLE


async def test_update_status_toggle(controller: ArchonController):
    assert controller.status & ControllerStatus.IDLE
    controller.update_status(ControllerStatus.POWERON, "toggle")
    assert not (controller.status & ControllerStatus.POWERON)


async def test_update_status_invalid(controller: ArchonController):
    with pytest.raises(ValueError):
        controller.update_status(ControllerStatus.IDLE, "bad_mode")
