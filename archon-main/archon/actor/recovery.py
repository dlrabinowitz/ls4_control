#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2023-12-01
# @Filename: recovery.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from __future__ import annotations

import asyncio
import json
import pathlib
from contextlib import contextmanager
from copy import deepcopy
from os import PathLike

from typing import TYPE_CHECKING, Sequence

from clu.command import Command
from sdsstools import get_sjd

from archon.actor.delegate import ExposureDelegate
from archon.controller.controller import ArchonController


if TYPE_CHECKING:
    import nptyping

    from archon.actor.actor import ArchonBaseActor
    from archon.actor.delegate import FetchDataDict

    BufferDataType = nptyping.NDArray[nptyping.Shape["*,*"], nptyping.UInt]


class ExposureRecovery:
    """A mechanism for recovering exposures that failed to write to disk.

    When the `.ExposureDelegate` finishes reading a buffer and compiling the
    header, all the metadata (excluding the data itself) is stored in a
    JSON file with the same name as the final image. During actor start,
    `.ExposeureRecovery` looks for missing JSON files which indicate
    FITS files not fully written. If found, the buffer is read again and the
    FITS file is written to disk using the information stored in the JSON file.

    """

    def __init__(self, controllers: dict[str, ArchonController]) -> None:
        self.controllers = controllers
        self._command: Command | ArchonBaseActor | None = None

        # An event that gets cleared (becomes blocking) when the recovery
        # is in progress. We begin with it being set.
        self.locker = asyncio.Event()
        self.locker.set()

    @contextmanager
    def set_command(self, command: Command | ArchonBaseActor):
        """Sets the command or actor to use to output messages."""

        self._command = command
        yield
        self._command = None

    def emit(self, message_string: str, level: str = "d"):
        """Emits a message using the command or actor."""

        if self._command is None:
            return

        self._command.write(level, message={"text": message_string})

    def update(self, fetch_data: FetchDataDict | Sequence[FetchDataDict]):
        """Creates/updates the JSON file for a CCD image."""

        fetch_data = self._sequencify(fetch_data)

        for data in fetch_data:
            json_path = self._get_path(data)
            json_path.parent.mkdir(parents=True, exist_ok=True)

            dump_data = dict(deepcopy(data))
            del dump_data["data"]

            # This overwrite the entire JSON file.
            with open(json_path, "w") as json_file:
                json.dump(dump_data, json_file, indent=4, sort_keys=True)

            self.emit(f"Created lock JSON file {json_path!s}")

    def unlink(
        self,
        input: FetchDataDict | Sequence[FetchDataDict] | str | PathLike,
        force: bool = False,
    ):
        """Removes a JSON file once the FITS file has been written.

        Parameters
        ----------
        input
            The `.FetchDataDict` for the CCD to remove, or a sequence of fetched
            data. It can also be a single string or path to the FITS file, in which
            case its corresponding lock file will be deleted.
        force
            If ``False``, an error will be raised if the FITS file does not exist.

        Raises
        ------
        FileExistsError
            If the FITS file does not exist and ``force=False``.

        """

        # If we provide a FITS filename we get the lock filename and delete it.
        if isinstance(input, (str, PathLike)):
            lock_path = self._get_path(input)
            lock_path.unlink(missing_ok=True)
            self.emit(f"Removed lock JSON file {lock_path!s}.")
            return

        # Otherwise we assume we are passing a FetchDataDict or a sequence of them.
        fetch_data = self._sequencify(input)

        for data in fetch_data:
            fits_path = pathlib.Path(data["filename"]).absolute()
            lock_path = self._get_path(data)

            if force is False:
                if not fits_path.exists():
                    raise FileExistsError(
                        f"FITS file {fits_path!s} does not exist. "
                        "Not removing the JSON recovery file."
                    )

            lock_path.unlink(missing_ok=True)
            self.emit(f"Removed lock JSON file {lock_path!s}.")

    async def recover(
        self,
        controller_info: dict,
        path: str | PathLike | None = None,
        files: list[str | PathLike] | None = None,
        delete_lock: bool = True,
        write_async: bool = True,
        write_engine: str = "astropy",
        write_checksum: bool = False,
        checksum_mode: str = "md5",
        checksum_file: str | None = None,
        excluded_cameras: list[str] = [],
    ):
        """Recovers exposures from a JSON file.

        Parameters
        ----------
        controller_info
            A dictionary with the controller-to-CCD mapping and information.
        path
            A directory containing lock files. All lock files found will be recovered.
        files
            A list of lock files to recover.
        delete_lock
            If ``True``, the JSON file will be removed after a successful recovery.
        write_async
            Whether to write the FITS file asynchronously.
        write_engine
            The engine to use to write the FITS file, either ``astropy`` or ``fitsio``.
        write_checksum
            Whether to update the checksum file with the recovered image checksum.
        checksum_mode
            The algorithm to use to generate the checksum.
        checksum_file
            The name or template for the checksum file. If ``None``, the default is
            use. The template can contain the ``{SJD}`` keyword, which will be
            set to the current SJD. The checksum is always relative to the parent
            directory of the recovered image.
        excluded_cameras
            A list of cameras to exclude from the recovery.

        Returns
        -------
        filenames
            A list with the filenames of the recovered images.

        """

        if path is not None and files is not None:
            raise ValueError("Cannot specify both path and files.")

        if path is not None:
            path = pathlib.Path(path).absolute()
            if path.is_dir():
                lock_files = list(path.glob("*.lock"))
            else:
                lock_files = [path]
        elif files is not None:
            lock_files = [pathlib.Path(f).absolute() for f in files]
        else:
            raise ValueError("Must specify either path or files.")

        buffer_cache: dict[int, BufferDataType] = {}
        recovered: list[pathlib.Path] = []

        self.locker.clear()

        for lock_file in lock_files:
            if not lock_file.exists():
                self.emit(f"Lock file {lock_file!s} does not exist. Skipping.", "w")
                continue

            with open(lock_file, "r") as json_file:
                fdata: FetchDataDict = json.loads(json_file.read())

            controller_name = fdata["controller"]
            if controller_name not in self.controllers:
                self.emit(
                    f"Cannot recover {lock_file!r}. "
                    f"Controller {controller_name!r} not found.",
                    "w",
                )
                continue

            controller = self.controllers[controller_name]

            buffer = fdata["buffer"]
            if buffer not in buffer_cache:
                self.emit(f"Reading buffer {buffer}.")
                data: BufferDataType = await controller.fetch(buffer_no=buffer)
                buffer_cache[buffer] = data
            else:
                data = buffer_cache[buffer]

            ccd_data = ExposureDelegate._get_ccd_data(
                data,
                controller,
                fdata["ccd"],
                controller_info[controller.name],
            )
            fdata["data"] = ccd_data

            try:
                filename = fdata["filename"]
                self.emit(f"Writing recovered exposure {filename!r}.")
                result = await ExposureDelegate.write_to_disk(
                    fdata,
                    write_async=write_async,
                    write_engine=write_engine,
                    excluded_cameras=excluded_cameras,
                )
            except Exception as err:
                self.emit(f"Failed to write recovered exposure: {err!r}", "w")
                continue

            if result is None:
                self.emit(f"Skipping exposure {filename!r} (excluded_cameras).", "w")
                continue

            # Update checksum file.
            if write_checksum:
                checksum_file = checksum_file or f"{{SJD}}.{checksum_mode}sum"
                checksum_file = checksum_file.format(SJD=get_sjd())
                await ExposureDelegate._generate_checksum(
                    checksum_file,
                    [filename],
                    mode=checksum_mode,
                )

            self.emit(f"Exposure {filename!r} has been recovered and saved.")
            recovered.append(pathlib.Path(filename))

            if delete_lock:
                self.unlink(fdata)

        self.locker.set()

        return recovered

    def _sequencify(self, fetch_data: FetchDataDict | Sequence[FetchDataDict]):
        """Makes sure ``fetch_data`` is a list of `.FetchDataDict`."""

        if not isinstance(fetch_data, Sequence):
            fetch_data = [fetch_data]
        else:
            fetch_data = list(fetch_data)

        return fetch_data

    def _get_path(self, fetch_data: FetchDataDict | str | PathLike):
        """Returns the path to the JSON file for a given image."""

        if isinstance(fetch_data, dict):
            fn = fetch_data["filename"]
        else:
            fn = fetch_data

        return pathlib.Path(str(fn) + ".lock").absolute()
