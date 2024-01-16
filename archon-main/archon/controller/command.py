#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2021-01-20
# @Filename: command.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from __future__ import annotations

import asyncio
import enum
import re
import warnings

from typing import AsyncGenerator, Optional

from archon.exceptions import ArchonError, ArchonUserWarning
from archon.tools import Timer

from . import MAX_COMMAND_ID


__all__ = ["ArchonCommand", "ArchonCommandStatus", "ArchonCommandReply"]

REPLY_RE = re.compile(b"^([<|?])([0-9A-F]{2})(:?)(.*)\n?")


class ArchonCommandStatus(enum.Enum):
    """Status of an Archon command."""

    DONE = enum.auto()
    FAILED = enum.auto()
    RUNNING = enum.auto()
    TIMEDOUT = enum.auto()


class ArchonCommand(asyncio.Future):
    """Tracks the status and replies to a command sent to the Archon.

    ``ArchonCommand`` is a `~asyncio.Future` and can be awaited, at which point the
    command will have completed or failed.

    Parameters
    ----------
    command_string
        The command to send to the Archon. Will be converted to uppercase.
    command_id
        The command id to associate with this message.
    controller
        The controller that is running this command.
    expected_replies
        How many replies to expect from the controller before the command is done.
    timeout
        Time without receiving a reply after which the command will be timed out.
        `None` disables the timeout.
    """

    def __init__(
        self,
        command_string: str,
        command_id: int,
        controller=None,
        expected_replies: Optional[int] = 1,
        timeout: Optional[float] = None,
    ):
        super().__init__()

        self.command_string = command_string.upper()
        self.command_id = command_id
        self.controller = controller
        self._expected_replies = expected_replies

        #: List of str or bytes: List of replies received for this command.
        self.replies: list[ArchonCommandReply] = []

        #: .ArchonCommandStatus: The status of the command.
        self.status = ArchonCommandStatus.RUNNING

        if self.command_id < 0 or self.command_id > MAX_COMMAND_ID:
            raise ValueError(
                f"command_id must be between 0x00 and 0x{MAX_COMMAND_ID:X}"
            )

        self.timer: Optional[Timer] = Timer(timeout, self._timeout) if timeout else None
        self.__event = asyncio.Event()

    @property
    def raw(self):
        """Returns the raw command sent to the Archon (without the newline)."""

        return f">{self.command_id:02X}{self.command_string}"

    def process_reply(self, reply: bytes) -> ArchonCommandReply | None:
        """Processes a new reply to this command.

        The Archon can reply to a command of the form ``>xxCOMMAND`` (where ``xx``
        is a 2-digit hexadecimal) with ``?xx`` to indicate failure or ``<xxRESPONSE``.
        In the latter case the ``RESPONSE`` ends with a newline. The Archon can also
        reply with ``<xx:bbbbb...bbbb`` with the ``:`` indicating that what follows is
        a binary string with 1024 characters. In this case the reply does not end with
        a newline.

        Parameters
        ----------
        reply
            The received reply, as bytes.
        """

        try:
            archon_reply = ArchonCommandReply(reply, self)
        except ArchonError as err:
            warnings.warn(str(err), ArchonUserWarning)
            self._mark_done(self.status.FAILED)
            return

        if archon_reply.command_id != self.command_id:
            warnings.warn(
                f"Received reply to command {self.raw} that does not match "
                f"the command id: {reply.decode()}",
                ArchonUserWarning,
            )
            self._mark_done(self.status.FAILED)
            return

        self.replies.append(archon_reply)
        self.__event.set()  # Release the event to indicate a new reply has been added.
        if self.timer:
            self.timer.reset()

        if archon_reply.type == "?":
            self._mark_done(self.status.FAILED)
            return archon_reply

        if self._expected_replies and len(self.replies) == self._expected_replies:
            self._mark_done()

        return archon_reply

    async def get_replies(self) -> AsyncGenerator[ArchonCommandReply, None]:
        """Yields an asynchronous generator of replies as they are produced."""

        n_output = 0

        while True:
            await self.__event.wait()
            if len(self.replies) > n_output:
                yield self.replies[-1]
                n_output += 1
            if self.done():
                break
            else:
                self.__event.clear()

    def succeeded(self):
        """Reports the command success status.

        Returns `True` if the command succeeded, or `False` if it failed, timed out, or
        if the command is not yet done.
        """

        return self.status == self.status.DONE

    def _mark_done(self, status: ArchonCommandStatus = ArchonCommandStatus.DONE):
        """Marks the command done with ``status``."""

        # Release the event one last time to let the loop to finish and cancel timer.
        self.__event.set()
        if self.timer:
            self.timer.cancel()

        self.status = status
        if not self.done():
            self.set_result(self)

        # Return ID to the pool
        if self.controller:
            self.controller._id_pool.add(self.command_id)

    def _timeout(self):
        """Marks the command timed out."""

        self._mark_done(self.status.TIMEDOUT)

    def __repr__(self):
        return f"<ArchonCommand ({self.raw}, status={self.status})>"


class ArchonCommandReply:
    """A reply received from the Archon to a given command.

    When ``str(archon_command_reply)`` is called, the reply (without the reply code or
    command id) is returned, except when the reply is binary in which case an error
    is raised.

    Parameters
    ----------
    raw_reply
        The raw reply received from the Archon.
    command
        The command associated with the reply.

    Raise
    -----
    .ArchonError
        Raised if the reply cannot be parsed.
    """

    def __init__(self, raw_reply: bytes, command: ArchonCommand):
        parsed = REPLY_RE.match(raw_reply)
        if not parsed:
            raise ArchonError(
                f"Received unparseable reply to command " f"{command.raw}: {raw_reply}"
            )

        self.command = command
        self.raw_reply = raw_reply

        rtype, rcid, rbin, rmessage = parsed.groups()
        self.type: str = rtype.decode()
        self.command_id: int = int(rcid, 16)
        self.is_binary: bool = rbin.decode() == ":"

        self.reply: str | bytes
        if self.is_binary:
            # If the reply is binary, remove the prefixes and save the full
            # content as the reply.
            self.reply = raw_reply.replace(b"<" + rcid + b":", b"")
        else:
            self.reply = rmessage.decode().strip()

    def __str__(self) -> str:
        if isinstance(self.reply, bytes):
            raise ArchonError("The reply is binary and cannot be converted to string.")
        return self.reply

    def __repr__(self):
        return f"<ArchonCommandReply ({self.raw_reply})>"
