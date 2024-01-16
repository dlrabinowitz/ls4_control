#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2021-09-04
# @Filename: test_command_system.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from archon.actor import ArchonActor
from archon.exceptions import ArchonError


async def test_system(actor: ArchonActor):
    command = await actor.invoke_mock_command("system")
    await command

    assert command.status.did_succeed
    assert len(command.replies) == 3


async def test_system_fail_controller(actor: ArchonActor):
    await actor.controllers["sp1"].stop()

    command = await actor.invoke_mock_command("system")
    await command

    assert command.status.did_fail


async def test_system_fails(actor: ArchonActor, mocker):
    mocker.patch.object(actor.controllers["sp1"], "get_system", side_effect=ArchonError)

    command = await actor.invoke_mock_command("system")
    await command

    assert command.status.did_fail
