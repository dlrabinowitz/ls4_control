#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2021-01-21
# @Filename: actor.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from __future__ import annotations

import asyncio
import os
import pathlib
import warnings
from contextlib import suppress

from typing import ClassVar, Dict, Type

import astropy.time
import click

from clu import Command
from clu.actor import AMQPActor, BaseActor
from sdsstools import get_sjd
from sdsstools.configuration import Configuration

from archon import __version__
from archon.actor.recovery import ExposureRecovery
from archon.controller.command import ArchonCommand
from archon.controller.controller import ArchonController
from archon.exceptions import ArchonUserWarning

from .commands import parser as archon_command_parser
from .delegate import ExposureDelegate


__all__ = ["ArchonBaseActor", "ArchonActor"]


class ArchonBaseActor(BaseActor):
    """Archon controller base actor.

    This class is intended to be subclassed with a specific actor class (normally
    ``AMQPActor`` or ``LegacyActor``).

    Parameters
    ----------
    controllers
        The list of `.ArchonController` instances to manage.
    """

    parser: ClassVar[click.Group] = archon_command_parser
    is_legacy: bool = False

    BASE_CONFIG: ClassVar[str | Dict | None] = None
    DELEGATE_CLASS: ClassVar[Type[ExposureDelegate]] = ExposureDelegate
    CONTROLLER_CLASS: ClassVar[Type[ArchonController]] = ArchonController

    def __init__(
        self,
        *args,
        controllers: tuple[ArchonController, ...] = (),
        run_recovery_on_start: bool = True,
        **kwargs,
    ):
        #: dict[str, ArchonController]: A mapping of controller name to controller.
        self.controllers = {c.name: c for c in controllers}

        self.parser_args = [self.controllers]

        if "schema" not in kwargs:
            kwargs["schema"] = os.path.join(
                os.path.dirname(__file__),
                "../etc/schema.json",
            )

        super().__init__(*args, **kwargs)

        self.observatory = os.environ.get("OBSERVATORY", "LCO")
        self.version = __version__

        # Issue status and system on a loop.
        # self.timed_commands.add_command("status", delay=60)  # type: ignore
        # self.timed_commands.add_command("system", delay=60)  # type: ignore

        self.exposure_delegate = self.DELEGATE_CLASS(self)

        self.run_recovery_on_start = run_recovery_on_start
        self.exposure_recovery = ExposureRecovery(self.controllers)

        self._fetch_log_jobs = []
        self._status_jobs = []

        self.config_file_path: str | None = None

    async def start(self):
        """Start the actor and connect the controllers."""

        connect_timeout = self.config["timeouts"]["controller_connect"]
        connect_timeout = 10

        for controller in self.controllers.values():
            try:
                await asyncio.wait_for(controller.start(), timeout=connect_timeout)
            except asyncio.TimeoutError:
                warnings.warn(
                    f"Timeout out connecting to {controller.name!r}.",
                    ArchonUserWarning,
                )
            except Exception as err:
                warnings.warn(
                    f"Failed connecting to controller {controller.name} at "
                    f"{controller.host}: {err}",
                    ArchonUserWarning,
                )

        await super().start()

        self._fetch_log_jobs = [
            asyncio.create_task(self._fetch_log(controller))
            for controller in self.controllers.values()
        ]

        self._status_jobs = [
            asyncio.create_task(self._report_status(controller))
            for controller in self.controllers.values()
        ]

        # Depending on how the actor is initialised exposure_recovery may not have
        # been set with the actual controllers.
        self.exposure_recovery.controllers = self.controllers
        if self.run_recovery_on_start:
            await self._recover_exposures()

    async def stop(self):
        with suppress(asyncio.CancelledError):
            for task in self._fetch_log_jobs:
                task.cancel()
                await task

        for controller in self.controllers.values():
            await controller.stop()

        return await super().stop()

    @classmethod
    def from_config(cls, config, *args, **kwargs):
        """Creates an actor from a configuration file."""

        if config is None:
            if cls.BASE_CONFIG is None:
                raise RuntimeError("The class does not have a base configuration.")
            config = cls.BASE_CONFIG

        instance = super(ArchonBaseActor, cls).from_config(config, *args, **kwargs)

        if isinstance(config, (str, pathlib.Path)):
            instance.config_file_path = str(config)
        elif isinstance(config, Configuration):
            instance.config_file_path = str(
                config._BASE_CONFIG_FILE
                if config._BASE_CONFIG_FILE
                else config._CONFIG_FILE
            )

        assert isinstance(instance, ArchonBaseActor)
        assert isinstance(instance.config, dict)

        enabled_controllers = instance.config.get("enabled_controllers", None)

        if "controllers" in instance.config:
            controllers = (
                cls.CONTROLLER_CLASS(
                    ctrname,
                    ctr["host"],
                    ctr["port"],
                    config=instance.config,
                )
                for (ctrname, ctr) in instance.config["controllers"].items()
                if enabled_controllers is not None and ctrname in enabled_controllers
            )
            instance.controllers = {c.name: c for c in controllers}
            instance.parser_args = [instance.controllers]  # Need to refresh this

        return instance

    async def _fetch_log(self, controller: ArchonController):  # pragma: no cover
        """Fetches the log and outputs new messages.

        This is not implemented as a timed command because we don't want a new command
        popping up and running every second. We write to all users only when there's
        a new log.
        """

        while True:
            if not controller.is_connected():
                await asyncio.sleep(1)
                continue
            cmd: ArchonCommand = await controller.send_command("FETCHLOG")
            if cmd.succeeded() and len(cmd.replies) == 1:
                if str(cmd.replies[0].reply) not in ["(null)", ""]:
                    self.write(
                        log=dict(
                            controller=controller.name,
                            log=str(cmd.replies[0].reply),
                        )
                    )
                    continue  # There may be more messages, so don't wait.
            await asyncio.sleep(1)

    async def _report_status(self, controller: ArchonController):
        """Reports the status of the controller."""

        async for status in controller.yield_status():
            self.write(
                message_code="d",
                status=dict(
                    controller=controller.name,
                    status=status.value,
                    status_names=[flag.name for flag in status.get_flags()],
                ),
            )

    async def _recover_exposures(self):
        """Recovers any failed exposures for the current MJD."""

        now = astropy.time.Time.now()
        mjd = get_sjd() if self.config.get("files.use_sjd", False) else int(now.mjd)
        data_dir = pathlib.Path(self.config.get("files.data_dir", "/data"))

        mjd_dir = data_dir / str(mjd)
        if not mjd_dir.exists():
            self.write("w", f"Cannot find directory for MJD {mjd}. Skipping recovery.")
            return

        with self.exposure_recovery.set_command(self):
            recovered = await self.exposure_recovery.recover(
                self.config["controllers"],
                path=mjd_dir,
                write_checksum=self.config["checksum.write"],
                checksum_mode=self.config["checksum.mode"],
                checksum_file=self.config["checksum.file"],
            )

        return recovered


class ArchonActor(ArchonBaseActor, AMQPActor):
    """Archon actor based on the AMQP protocol."""

    pass


ArchonCommandType = Command[ArchonActor]
