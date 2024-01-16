#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2021-09-03
# @Filename: test_command_init.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from archon.actor.actor import ArchonActor
from archon.exceptions import ArchonError


async def test_init(actor):
    command = await actor.invoke_mock_command("init")
    await command

    assert command.status.did_succeed
    assert actor.controllers["sp1"].acf_config is not None


async def test_init_controller_fails(actor):
    await actor.controllers["sp1"].stop()

    command = await actor.invoke_mock_command("init")
    await command

    assert command.status.did_fail


async def test_init_filename(actor, tmp_path):
    config_file = tmp_path / "test.acf"
    with open(config_file, "w") as f:
        f.write(
            """[CONFIG]
ADXCDS=0
ADXRAW=0
APPLYALL=0
BIGBUF=0
LINECOUNT=100
PIXELCOUNT=100
PARAMETER1="Lines=100"
PARAMETER2="Pixels=100"
"""
        )

    command = await actor.invoke_mock_command(f"init {str(config_file)}")
    await command

    assert command.status.did_succeed


async def test_init_bad_filename(actor):
    command = await actor.invoke_mock_command("init dir/badfile.acf")
    await command

    assert command.status.did_fail


async def test_init_write_fails(actor: ArchonActor, mocker):
    mocker.patch.object(
        actor.controllers["sp1"],
        "write_config",
        side_effect=ArchonError,
    )

    command = await actor.invoke_mock_command("init")
    await command

    assert command.status.did_fail


async def test_init_set_param_fails(actor: ArchonActor, mocker):
    mocker.patch.object(
        actor.controllers["sp1"],
        "set_param",
        side_effect=ArchonError,
    )

    command = await actor.invoke_mock_command("init")
    await command

    assert command.status.did_fail


async def test_init_empty_controllers(actor: ArchonActor):
    del actor.controllers["sp1"]

    command = await actor.invoke_mock_command("init")
    await command

    assert command.status.did_fail


async def test_init_invalid_controllers(actor: ArchonActor):
    command = await actor.invoke_mock_command("init --controller sp5")
    await command

    assert command.status.did_fail


async def test_init_with_overrides(actor):
    # Modify config file with overrides.
    actor.config["archon"]["acf_overrides"] = {"sp1": {"MOD11/HEATERATARGET": -200}}

    command = await actor.invoke_mock_command("init")
    await command

    assert command.status.did_succeed

    acf_config = actor.controllers["sp1"].acf_config
    assert acf_config is not None
    assert acf_config["CONFIG"]["MOD11\\HEATERATARGET"] == "-200"
