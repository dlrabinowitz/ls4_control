#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2021-01-20
# @Filename: conftest.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from __future__ import annotations

import asyncio
import configparser
import os
import re
import types

from typing import Iterable, Tuple, Union

import pytest_asyncio

from archon import config
from archon.controller.controller import ArchonController
from archon.controller.maskbits import ControllerStatus


CommandsType = Iterable[Tuple[str, Iterable[Union[str, bytes]]]]


@pytest_asyncio.fixture()
async def controller(request, unused_tcp_port: int):
    """Mocks a `.ArchonController` that replies to commands with predefined replies.

    Tests that use this fixture must be decorated with ``@pytest.mark.commands``. The
    arguments are a list of input commands and replies. For example
    ``@pytest.mark.commands.commands=[['STATUS', ['<{cid}VALID=1 COUNT=379780']]]``
    will reply with ``<01VALID=1 COUNT=379780\n`` to the commands ``>01STATUS``.
    The command of the reply can be hardcoded or use ``{cid}`` for a placeholder that
    will be replaced with the actual command id. If the reply is an instance of
    bytes, it will be returned as a binary response.
    """

    try:
        commands: CommandsType = request.node.get_closest_marker("commands").args[0]
    except AttributeError:
        commands: CommandsType = []

    async def handle_connection(
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        while True:
            try:
                data = await reader.readuntil()
            except (asyncio.IncompleteReadError, ConnectionResetError):
                break

            data = data.decode()

            matched = re.match(
                r"^>([0-9A-F]{2})(FRAME|SYSTEM|FASTLOADPARAM|PING|STATUS|FETCH|LOCK|"
                r"CLEARCONFIG|RCONFIG|RESETTIMING|HOLDTIMING|RELEASETIMING|APPLYCDS|"
                r"APPLYALL|POWERON|WCONFIG|POLLON|POLLOFF|APPLYMOD[0-9]+).*\n$",
                data,
            )
            if not matched:
                continue

            cid, com = matched.groups()

            found_command = False
            for command, replies in commands:
                if command.upper() == com.upper():
                    if isinstance(replies, str):
                        replies = [replies]
                    for reply in replies:
                        if isinstance(reply, str):
                            reply = (reply.format(cid=cid) + "\n").encode()
                        else:
                            reply = reply.replace(b"{cid}", cid.encode()).ljust(
                                1028, b" "
                            )
                        writer.write(reply)
                        await writer.drain()
                        found_command = True
                    break

            # Default reply
            if not found_command:
                if com.upper() == "STATUS":
                    writer.write(f"<{cid}POWER=4 POWERGOOD=1\n".encode())
                else:
                    writer.write(f"<{cid}\n".encode())
                await writer.drain()

        writer.close()
        await writer.wait_closed()

    server = await asyncio.start_server(handle_connection, "localhost", unused_tcp_port)

    async with server:
        archon = ArchonController("sp1", "localhost", unused_tcp_port)

        config["archon"]["default_parameters"]["Exposures"] = 0
        # config._CONFIG_FILE = tempfile.NamedTemporaryFile().name

        archon.start = types.MethodType(start_archon, archon)

        await archon.start()

        yield archon

        await archon.stop()


async def start_archon(self, **kwargs):
    await ArchonController.start(self, reset=False, read_acf=False)

    acf_config = configparser.ConfigParser()
    acf_config.read(os.path.join(os.path.dirname(__file__), "data/BOSS_extra.acf"))
    self.acf_config = acf_config

    self._parse_params()
    await self._set_default_window_params(reset=False)

    # Add some fake ACF info from a file.
    self._status = ControllerStatus.IDLE | ControllerStatus.POWERON
