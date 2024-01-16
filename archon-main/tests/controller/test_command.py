#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2021-01-24
# @Filename: test_command.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

import asyncio

import pytest

from archon.controller.command import ArchonCommand
from archon.exceptions import ArchonUserWarning


@pytest.mark.parametrize("command_id", [-5, 2**8 + 1])
def test_command_bad_command_id(command_id):
    with pytest.raises(ValueError):
        ArchonCommand("ping", command_id)


@pytest.mark.parametrize("reply", [b"bad_reply", b"<02PONG"])
def test_command_process_bad_reply(reply):
    command = ArchonCommand("ping", 1)

    with pytest.warns(ArchonUserWarning):
        command.process_reply(reply)

    assert command.status == command.status.FAILED


def test_command_process_reply_failed():
    command = ArchonCommand("ping", 1)
    command.process_reply(b"?01")
    assert command.status == command.status.FAILED


async def test_command_two_replies():
    command = ArchonCommand("ping", 1, expected_replies=2, timeout=0.1)
    assert command.status == command.status.RUNNING
    command.process_reply(b"<01pong1")
    assert command.status == command.status.RUNNING
    await asyncio.sleep(0.01)
    command.process_reply(b"<01pong2")
    assert command.status == command.status.DONE


async def test_command_timeout():
    command = ArchonCommand("ping", 1, expected_replies=2, timeout=0.01)
    assert command.status == command.status.RUNNING
    await asyncio.sleep(0.02)
    assert command.status == command.status.TIMEDOUT


async def test_command_get_replies():
    async def background(command: ArchonCommand):
        command.process_reply(b"<01pong1")
        await asyncio.sleep(0.01)
        command.process_reply(b"<01pong1")
        await asyncio.sleep(0.02)
        command._mark_done()

    command = ArchonCommand("ping", 1, expected_replies=None)
    asyncio.create_task(background(command))

    replies = []
    async for reply in command.get_replies():
        replies.append(reply)

    assert command.succeeded()
    assert len(replies) == 2
