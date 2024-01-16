#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2021-09-04
# @Filename: test_command_config.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from archon.actor import ArchonActor
from archon.exceptions import ArchonError


SAMPLE_CONFIG = r"""[CONFIG]
CONFIG\1=1
CONFIG\2="2,2"
LINECOUNT=100
PIXELCOUNT=100
PARAMETER1="Lines=100"
PARAMETER2="Pixels=100"
"""


async def test_config_read(actor: ArchonActor, mocker):
    mocker.patch.object(
        actor.controllers["sp1"],
        "read_config",
        return_value=(None, SAMPLE_CONFIG.splitlines()),
    )

    command = await actor.invoke_mock_command("config read sp1")
    await command

    assert command.status.did_succeed
    assert command.replies[-1].message["config"]["config"] == SAMPLE_CONFIG.splitlines()


async def test_config_read_save(actor: ArchonActor, mocker):
    mocker.patch.object(
        actor.controllers["sp1"],
        "read_config",
        return_value=(None, SAMPLE_CONFIG.splitlines()),
    )

    command = await actor.invoke_mock_command("config read sp1 --save")
    await command

    assert command.status.did_succeed


async def test_config_read_fails(actor: ArchonActor, mocker):
    mocker.patch.object(
        actor.controllers["sp1"],
        "read_config",
        side_effect=ArchonError,
    )

    command = await actor.invoke_mock_command("config read sp1")
    await command

    assert command.status.did_fail


async def test_config_read_bad_controller_name(actor: ArchonActor):
    command = await actor.invoke_mock_command("config read sp5")
    await command

    assert command.status.did_fail


async def test_config_read_fail_controller(actor: ArchonActor):
    await actor.controllers["sp1"].stop()

    command = await actor.invoke_mock_command("config read sp1")
    await command

    assert command.status.did_fail


async def test_config_write(actor: ArchonActor, tmp_path):
    config_temp = tmp_path / "config.acf"
    config_temp.write_text(SAMPLE_CONFIG)

    command = await actor.invoke_mock_command(f"config write sp1 {str(config_temp)}")
    await command

    assert command.status.did_succeed


async def test_config_write_fails(actor: ArchonActor, mocker, tmp_path):
    config_temp = tmp_path / "config.acf"
    config_temp.touch()

    mocker.patch.object(
        actor.controllers["sp1"],
        "write_config",
        side_effect=ArchonError,
    )

    command = await actor.invoke_mock_command(f"config write sp1 {str(config_temp)}")
    await command

    assert command.status.did_fail


async def test_config_write_bad_controller_name(actor: ArchonActor, tmp_path):
    config_temp = tmp_path / "config.acf"
    config_temp.touch()

    command = await actor.invoke_mock_command(f"config write sp5 {str(config_temp)}")
    await command

    assert command.status.did_fail


async def test_config_write_fail_controller(actor: ArchonActor, tmp_path):
    config_temp = tmp_path / "config.acf"
    config_temp.touch()

    await actor.controllers["sp1"].stop()

    command = await actor.invoke_mock_command(f"config write sp1 {str(config_temp)}")
    await command

    assert command.status.did_fail
