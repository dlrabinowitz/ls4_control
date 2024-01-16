#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2021-01-20
# @Filename: tools.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from __future__ import annotations

import asyncio
import os
import pathlib
import socket
from subprocess import CalledProcessError


__all__ = [
    "Timer",
    "gzip_async",
    "subprocess_run_async",
    "get_profile_name",
    "send_and_receive",
]


class Timer:
    """An asynchronous timer."""

    def __init__(self, timeout: float, callback):
        self._timeout = timeout
        self._callback = callback

        self._loop = asyncio.get_event_loop()
        self._task: asyncio.Task | None = None

        self.reset()

    async def _job(self):
        await asyncio.sleep(self._timeout)
        try:
            await self._callback()
        except TypeError:  # Happens when the callback becomes None during an error.
            pass

    def cancel(self):
        """Cancel the timer."""

        if self._task:
            self._task.cancel()

    def reset(self):
        """Reset the count."""

        self.cancel()
        self._task = self._loop.create_task(self._job())


async def subprocess_run_async(*args, shell=False, cwd=None):
    """Runs a command asynchronously.

    If ``shell=True`` the command will be executed through the shell. In that case
    the argument must be a single string with the full command. Otherwise, must receive
    a list of program arguments. Returns the output of stdout.
    """

    if shell:
        cmd = await asyncio.create_subprocess_shell(
            args[0],
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        cmd_str = args[0]

    else:
        cmd = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        cmd_str = " ".join(args)

    stdout, stderr = await cmd.communicate()
    if cmd.returncode and cmd.returncode > 0:
        raise CalledProcessError(
            cmd.returncode,
            cmd=cmd_str,
            output=stdout,
            stderr=stderr,
        )

    if stdout:
        return stdout.decode()


async def gzip_async(file: pathlib.Path | str, complevel=1, suffix: str | None = None):
    """Compresses a file with gzip asynchronously."""

    file = str(file)
    if not os.path.exists(file):
        raise FileNotFoundError(f"File not found: {file!r}")

    try:
        parts = [
            "gzip",
            "-" + str(complevel),
            file,
        ]
        if suffix is not None:
            parts += [f"--suffix={suffix}"]
        await subprocess_run_async(*parts)
    except Exception as err:
        raise OSError(f"Failed compressing file {file}: {err}")


def get_profile_name() -> str:  # pragma: no cover
    """Determines the profile to use from the domain name."""

    fqdn = socket.getfqdn()

    if fqdn.startswith("obsvld01"):
        return "lvm"
    elif fqdn.endswith("sdss5-boss-icc.lco.cl"):
        return "boss"
    elif fqdn.endswith("lco.cl"):
        return "lvm"

    raise RuntimeError(f"Cannot infer profile from domain {fqdn!r}.")


async def send_and_receive(
    host: str,
    port: int,
    data: bytes,
    timeout=1,
    delimiter=b"\n",
):
    """Establishes a connection to a server, sends data, and returns the reply."""

    w = None

    try:
        r, w = await asyncio.wait_for(asyncio.open_connection(host, port), 1)

        w.write(data)
        await w.drain()

        reply = await asyncio.wait_for(r.readuntil(delimiter), timeout)

        return reply
    except Exception:
        return False
    finally:
        if w is not None:
            w.close()
            await w.wait_closed()
