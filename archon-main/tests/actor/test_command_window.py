#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2022-04-29
# @Filename: test_command_window.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

import pytest

from archon.actor import ArchonActor


async def test_get_window(actor: ArchonActor):
    command = await actor.invoke_mock_command("get-window")
    await command

    assert command.status.did_succeed
    assert len(command.replies) == 2


async def test_get_window_no_controllers(actor: ArchonActor):
    actor.controllers.pop("sp1")

    command = await actor.invoke_mock_command("get-window")
    await command

    assert command.status.did_fail


async def test_set_window(actor: ArchonActor, mocker):
    command = await actor.invoke_mock_command("set-window  --lines 50")
    await command

    assert command.status.did_succeed
    assert actor.controllers["sp1"].current_window["lines"] == 50


@pytest.mark.parametrize("window_mode", ["default", ""])
async def test_set_window_default(actor: ArchonActor, window_mode: str, mocker):
    reset = mocker.patch.object(actor.controllers["sp1"], "reset_window")

    command = await actor.invoke_mock_command(f"set-window {window_mode}")
    await command

    assert command.status.did_succeed
    reset.assert_called()


async def test_set_window_mode(actor: ArchonActor, mocker):
    set_window = mocker.patch.object(actor.controllers["sp1"], "set_window")

    command = await actor.invoke_mock_command("set-window test_mode")
    await command

    assert command.status.did_succeed
    set_window.assert_called()


async def test_set_window_mode_bad_mode(actor: ArchonActor, mocker):
    set_window = mocker.patch.object(actor.controllers["sp1"], "set_window")

    command = await actor.invoke_mock_command("set-window bad_mode")
    await command

    assert command.status.did_fail
    set_window.assert_not_called()
