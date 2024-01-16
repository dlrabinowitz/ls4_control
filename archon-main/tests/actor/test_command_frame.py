#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2021-09-04
# @Filename: test_command_frame.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from archon.actor import ArchonActor
from archon.exceptions import ArchonError


async def test_config_frame_status(actor: ArchonActor):
    command = await actor.invoke_mock_command("frame status sp1")
    await command

    assert command.status.did_succeed


async def test_config_frame_status_fails(actor: ArchonActor, mocker):
    mocker.patch.object(actor.controllers["sp1"], "get_frame", side_effect=ArchonError)

    command = await actor.invoke_mock_command("frame status sp1")
    await command

    assert command.status.did_fail


async def test_config_frame_status_bad_controller_name(actor: ArchonActor):
    command = await actor.invoke_mock_command("frame status sp5")
    await command

    assert command.status.did_fail


async def test_config_frame_status_fail_controller(actor: ArchonActor):
    await actor.controllers["sp1"].stop()

    command = await actor.invoke_mock_command("frame status sp1")
    await command

    assert command.status.did_fail
