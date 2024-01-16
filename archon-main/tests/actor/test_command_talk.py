#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2021-09-04
# @Filename: test_command_talk.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

import pytest

from archon.actor import ArchonActor


async def test_talk(actor: ArchonActor):
    command = await actor.invoke_mock_command("talk STATUS")
    await command

    assert command.status.did_succeed
    assert len(command.replies) == 3


@pytest.mark.commands([["PING", ["?{cid}"]]])
async def test_talk_error(actor: ArchonActor):
    command = await actor.invoke_mock_command("talk PING")
    await command

    assert command.status.did_succeed
    assert len(command.replies) == 3
    assert command.replies[1].message_code == "e"


async def test_talk_fail_controller(actor: ArchonActor):
    await actor.controllers["sp1"].stop()

    command = await actor.invoke_mock_command("talk STATUS")
    await command

    assert command.status.did_fail
