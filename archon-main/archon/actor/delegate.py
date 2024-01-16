#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2021-05-30
# @Filename: delegate.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from __future__ import annotations

import asyncio
import os
import pathlib
import shutil
import subprocess
from contextlib import suppress
from dataclasses import dataclass, field
from functools import partial
from tempfile import NamedTemporaryFile
from time import time
from unittest.mock import MagicMock

from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Generic,
    List,
    Sequence,
    TypedDict,
    TypeVar,
)

import astropy.time
import numpy
from astropy.io import fits

from sdsstools.configuration import Configuration
from sdsstools.time import get_sjd

from archon import __version__
from archon.controller.controller import ArchonController
from archon.controller.maskbits import ControllerStatus
from archon.exceptions import ArchonError
from archon.tools import gzip_async, subprocess_run_async


if TYPE_CHECKING:
    import nptyping

    from clu import Command

    from .actor import ArchonBaseActor

    DataArray = nptyping.NDArray[nptyping.Shape["*,*"], nptyping.UInt16]


Actor_co = TypeVar("Actor_co", bound="ArchonBaseActor", covariant=True)


class FetchDataDict(TypedDict):
    """Dictionary of fetched data."""

    controller: str
    buffer: int
    ccd: str
    data: DataArray
    header: dict[str, list]
    exposure_no: int
    filename: str


@dataclass
class ExposeData:
    """Data about the ongoing exposure."""

    exposure_time: float
    flavour: str
    controllers: list[ArchonController]
    start_time: astropy.time.Time = field(default_factory=astropy.time.Time.now)
    end_time: astropy.time.Time | None = None
    mjd: int = 0
    exposure_no: int = 0
    header: Dict[str, Any] = field(default_factory=dict)
    delay_readout: int = 0
    window_mode: str | None = None
    window_params: dict = field(default_factory=dict)


class ExposureDelegate(Generic[Actor_co]):
    """Handles the exposure workflow."""

    def __init__(self, actor: Actor_co):
        self.actor = actor
        self.config = Configuration(actor.config.copy())

        self.expose_data: ExposeData | None = None

        self.use_shutter: bool = True
        self.is_writing: bool = False

        self.lock = asyncio.Lock()

        self._command: Command[Actor_co] | None = None
        self._expose_cotasks: asyncio.Task | None = None

        self._check_fitsio()

    @property
    def command(self):
        """Returns the current command."""

        if not self._command:
            raise AttributeError("Command not set")

        return self._command

    @command.setter
    def command(self, value: Command[Actor_co] | None):
        """Sets the current command."""

        self._command = value

    def reset(self):
        """Resets the exposure delegate."""

        self.expose_data = None
        self.command = None
        self.is_writing = False

        if self._expose_cotasks is not None and not self._expose_cotasks.done():
            self._expose_cotasks.cancel()

        self._expose_cotasks = None

        if self.lock.locked():
            self.lock.release()

    def fail(self, message: str | None = None):
        """Fails a command."""

        if message:
            self.command.fail(error=message)
        else:
            self.command.fail()

        self.reset()

        return False

    async def pre_expose(self, controllers: List[ArchonController]):
        """A routine that runs before integration begins."""

        return

    async def expose(
        self,
        command: Command[Actor_co],
        controllers: List[ArchonController],
        flavour: str = "object",
        exposure_time: float | None = 1.0,
        readout: bool = True,
        window_mode: str | None = None,
        window_params: dict = {},
        seqno: int | None = None,
        **readout_params,
    ) -> bool:
        self.command = command

        if self.lock.locked():
            return self.fail("The expose delegate is locked.")

        if flavour == "bias":
            exposure_time = 0.0
        else:
            if exposure_time is None:
                return self.fail(f"Exposure time required for flavour {flavour!r}.")

        if window_mode:
            if window_mode == "default":
                window_params = controllers[0].default_window.copy()
            elif window_mode in self.config.get("window_modes", []):
                extra_window_params = window_params.copy()
                window_params = self.config["window_modes"][window_mode]
                window_params.update(extra_window_params)
            else:
                return self.fail(f"Invalid window mode {window_mode!r}.")

        self.expose_data = ExposeData(
            exposure_time=exposure_time,
            flavour=flavour,
            controllers=controllers,
            window_params=window_params,
            window_mode=window_mode,
        )

        if not (await self.check_expose()):
            return False

        # Lock until the exposure is done.
        await self.lock.acquire()

        will_write = readout_params.get("write", True)
        if not self._set_exposure_no(controllers, increase=will_write, seqno=seqno):
            return False

        self.command.debug(next_exposure_no=self.expose_data.exposure_no)

        # If the exposure is a bias or dark we don't open the shutter, but
        # otherwise we add an extra timeout to allow for the code that handles
        # the shutter to open and close it and control the exposure time that way.
        if exposure_time == 0.0 or flavour == "bias":
            exposure_time = 0.0

        await self.pre_expose(controllers)

        try:
            self.command.debug("Setting exposure window.")
            await asyncio.gather(*[c.set_window(**window_params) for c in controllers])
        except BaseException as err:
            self.command.error("One controller failed setting the exposure window.")
            self.command.error(error=str(err))
            return self.fail()

        self._expose_cotasks = asyncio.create_task(self.expose_cotasks())

        expose_jobs = [
            asyncio.create_task(controller.expose(exposure_time, readout=False))
            for controller in controllers
        ]

        try:
            c_list = ", ".join([controller.name for controller in controllers])
            self.command.info(text=f"Starting exposure in controllers: {c_list}.")
            await asyncio.gather(*expose_jobs)
        except BaseException as err:
            self.command.error(error=str(err))
            self.command.error("One controller failed. Cancelling remaining tasks.")
            for job in expose_jobs:
                if not job.done():  # pragma: no cover
                    with suppress(asyncio.CancelledError):
                        job.cancel()
                        await job
            return self.fail()

        # Operate the shutter
        if self.use_shutter:
            if not (await self.shutter(True)):
                return self.fail("Shutter failed to open.")

        await asyncio.sleep(exposure_time)

        # Close shutter.
        if self.use_shutter:
            if not (await self.shutter(False)):
                return self.fail("Shutter failed to close.")

        if readout:
            return await self.readout(self.command, **readout_params)

        return True

    async def check_expose(self) -> bool:
        """Performs a series of checks to confirm we can expose."""

        assert self.expose_data

        for controller in self.expose_data.controllers:
            cname = controller.name
            if controller.status & ControllerStatus.EXPOSING:
                return self.fail(f"Controller {cname} is exposing.")
            elif controller.status & ControllerStatus.READOUT_PENDING:
                return self.fail(f"Controller {cname} has a read out pending.")
            elif controller.status & ControllerStatus.ERROR:
                return self.fail(f"Controller {cname} has status ERROR.")

        return True

    async def shutter(self, open=False) -> bool:
        """Operate the shutter."""

        return True

    async def readout(
        self,
        command: Command[Actor_co],
        extra_header={},
        delay_readout: int = 0,
        write: bool = True,
    ):
        """Reads the exposure, fetches the buffer, and writes to disk."""

        self.command = command

        # The command could be done at this point if we are doing an async readout.
        # In that case we would see an annoying warning. Instead let's replace the
        # command with an empty namespace.
        if self.command.done():
            self.command.set_status = MagicMock()

        if not self.lock.locked():
            return self.fail("Expose delegator is not locked.")

        if self.expose_data is None:
            return self.fail("No exposure data found.")

        controllers = self.expose_data.controllers

        self.expose_data.end_time = astropy.time.Time.now()
        self.expose_data.header = extra_header
        self.expose_data.delay_readout = delay_readout

        t0 = time()

        if any([c.status & ControllerStatus.EXPOSING for c in controllers]):
            return self.fail(
                "Found controllers exposing. Wait before reading or "
                "manually abort them."
            )

        try:
            command.info(text="Reading out CCDs.")
            readout_tasks = [
                controller.readout(
                    delay=self.expose_data.delay_readout,
                    notifier=self.command.debug,
                    idle_after=False,
                )
                for controller in controllers
            ]
            await asyncio.gather(*readout_tasks, self.readout_cotasks())

            command.debug(text="Fetching buffers.")
            c_fdata = await asyncio.gather(*[self.fetch_data(c) for c in controllers])

        except Exception as err:
            return self.fail(f"Failed reading out: {err}")

        self.command.debug(f"Readout completed in {time()-t0:.1f} seconds.")

        if write is False:
            self.command.warning("Not saving images to disk.")
            self.reset()
            return True

        # c_fdata is a list of lists. The top level list is one per controller,
        # the inner lists one per CCD. Since the inner list containes the name
        # of the controller we can flatten it now.
        fdata: list[FetchDataDict] = []
        for cf in c_fdata:
            fdata += cf

        self.command.debug(text="Calling post-process routine.")
        post_process_jobs = []
        for fdata_ccd in fdata:
            post_process_jobs.append(self.post_process(fdata_ccd))
        await asyncio.gather(*post_process_jobs)

        # Update save-point file after post-processing.
        self.actor.exposure_recovery.update(fdata)

        excluded_cameras: list[str] = self.config.get("excluded_cameras", [])
        write_engine: str = self.config.get("files.write_engine", "astropy")
        write_async: bool = self.config.get("files.write_async", True)

        self.command.debug(text="Writing data to file.")
        write_results: list = []
        write_coros = [
            self.write_to_disk(
                fd,
                excluded_cameras=excluded_cameras,
                write_async=write_async,
                write_engine=write_engine,
            )
            for fd in fdata
        ]

        # Prepare checksum information.
        write_checksum: bool = self.config["checksum.write"]
        checksum_mode: str = self.config.get("checksum.mode", "md5")
        checksum_file = self.config.get("checksum.file", f"{{SJD}}.{checksum_mode}sum")
        checksum_file: str = checksum_file.format(SJD=get_sjd())

        if self.config.get("files.write_async", True):
            coro_iter = asyncio.as_completed(write_coros)
        else:
            coro_iter = write_coros

        for coro in coro_iter:
            try:
                result = await coro
                write_results.append(result)

                # Delete save-point. We do it here because in case one of the
                # write coroutines crashes the actor.
                if isinstance(result, str):
                    fn = result
                    self.actor.exposure_recovery.unlink(fn)

                    # Update checksum file.
                    if write_checksum:
                        try:
                            await self._generate_checksum(
                                checksum_file,
                                [fn],
                                mode=checksum_mode,
                            )
                        except Exception as err:
                            self.command.warning(str(err))
                            continue

            except Exception as err:
                write_results.append(err)

        filenames: list[str] = []
        failed_to_write: bool = False
        for ii, result in enumerate(write_results):
            fn = fdata[ii]["filename"]
            ccd = fdata[ii]["ccd"]

            if isinstance(result, str):
                filenames.append(result)

            elif isinstance(result, Exception):
                self.command.error(f"Failed to writting {fn!s} to disk: {result!s}")
                failed_to_write = True

            elif result is None:
                self.command.warning(f"Not saving image for camera {ccd!r}.")

        self.command.info(filenames=filenames)

        self.reset()

        return not failed_to_write

    async def expose_cotasks(self):
        """Tasks that will be executed concurrently with readout.

        There is no guarantee that this coroutine will be waited or that
        it will complete before the shutter closes and the readout begins.
        To ensure that the expose tasks have completed, await the task
        in ``self._expose_cotasks``.

        """

        return

    async def readout_cotasks(self):
        """Tasks that will be executed concurrently with readout.

        This routine can be overridden to run processes that do not need to
        wait until `.post_process`. For example, reading out sensors and
        telescope data can happen here to save time.

        """

        return

    async def fetch_data(self, controller: ArchonController):
        """Fetches the buffer and compiles the header."""

        # Fetch buffer
        self.command.debug(text=f"Fetching {controller.name} buffer.")
        data, buffer_no = await controller.fetch(
            return_buffer=True,
            notifier=self.command.debug,
        )

        self.is_writing = True

        assert self.expose_data
        self.expose_data.header["BUFFER"] = [buffer_no, "The buffer number read"]

        controller_info = self.config["controllers"][controller.name]
        ccd_dict: list[FetchDataDict] = []
        for ccd_name in controller_info["detectors"]:
            ccd_header = await self.build_base_header(controller, ccd_name)
            ccd_data = self._get_ccd_data(data, controller, ccd_name, controller_info)
            ccd_dict.append(
                {
                    "controller": controller.name,
                    "buffer": buffer_no,
                    "ccd": ccd_name,
                    "data": ccd_data,
                    "header": ccd_header,
                    "exposure_no": self.expose_data.exposure_no,
                    "filename": self._get_ccd_filepath(controller, ccd_name),
                }
            )

        # Create a save-point file.
        self.actor.exposure_recovery.update(ccd_dict)

        return ccd_dict

    @staticmethod
    async def write_to_disk(
        ccd_data: FetchDataDict,
        excluded_cameras: list[str] = [],
        write_async: bool = True,
        write_engine: str = "astropy",
    ) -> str | None:
        """Writes ccd data to disk."""

        # Check if the CCD is in the list of excluded cameras. If so, raise.
        ccd = ccd_data["ccd"]
        if ccd in excluded_cameras:
            return None

        # Check file path and update header with exposure number and file name.
        file_path = ccd_data["filename"]

        if os.path.exists(file_path):
            raise ArchonError(f"Cannot overwrite file {file_path}.")

        header = ccd_data["header"]
        header["FILENAME"][0] = os.path.basename(file_path)
        header["EXPOSURE"][0] = ccd_data["exposure_no"]

        # Determine which engine to use to save the data.
        if write_engine == "astropy":
            writeto = partial(ExposureDelegate._write_file_astropy, ccd_data)
        elif write_engine == "fitsio":
            writeto = partial(ExposureDelegate._write_file_fitsio, ccd_data)
        else:
            raise ArchonError(f"Invalid write engine {write_engine!r}.")

        # Name of the temporary file where the data will be written to first.
        temp_file = NamedTemporaryFile(suffix=".fits", delete=True).name

        if write_async:
            loop = asyncio.get_event_loop()

            await loop.run_in_executor(None, writeto, temp_file)
            if file_path.endswith(".gz"):
                # astropy and fitsio are slow compressing ith gzip. Instead we
                # save the image uncompressed and then compress it manually.
                await gzip_async(temp_file, complevel=1, suffix=".gz")
                temp_file = temp_file + ".gz"

        else:
            writeto(temp_file)
            if file_path.endswith(".gz"):
                subprocess.run(f"gzip -1 {temp_file}", shell=True)
                temp_file = temp_file + ".gz"

        if not os.path.exists(temp_file):
            raise ArchonError(f"Failed writing image {file_path!s} to disk.")

        # Rename to final file.
        try:
            shutil.copyfile(temp_file, file_path)
        except Exception:
            raise ArchonError(
                f"Failed renaming temporary file {temp_file}. "
                "The original file is still available."
            )
        else:
            os.unlink(temp_file)

        return file_path

    @staticmethod
    def _write_file_astropy(data: FetchDataDict, file_path: str):
        """Writes the HDU to file using astropy."""

        header = fits.Header()
        for key, value in data["header"].items():
            header[key] = tuple(value) if isinstance(value, (list, tuple)) else value

        hdu = fits.PrimaryHDU(data["data"], header=header)
        hdu.writeto(file_path, checksum=True, overwrite=True)

        return

    @staticmethod
    def _write_file_fitsio(data: FetchDataDict, file_path: str):
        """Writes the HDU to file using astropy."""

        import fitsio

        header = []
        for key, value in data["header"].items():
            if isinstance(value, Sequence):
                header.append({"name": key, "value": value[0], "comment": value[1]})
            else:
                header.append({"name": key, "value": value, "comment": ""})

        with fitsio.FITS(file_path, "rw") as fits_:
            fits_.write(data["data"], header=header)
            fits_[-1].write_checksum()

        return

    @staticmethod
    async def _generate_checksum(
        checksum_file: str, filenames: list[str], mode: str = "md5"
    ):
        """Generates a checksum file for the images written to disk."""

        if mode.startswith("sha1"):
            sum_command = "sha1sum"
        elif mode.startswith("md5"):
            sum_command = "md5sum"
        else:
            raise ArchonError(f"Invalid checksum mode {mode!r}.")

        for filename in filenames:
            filename = str(filename)
            dirname = os.path.dirname(os.path.realpath(filename))
            basename = os.path.basename(filename)

            try:
                await subprocess_run_async(
                    f"{sum_command} {basename} >> {checksum_file}",
                    shell=True,
                    cwd=dirname,
                )
            except Exception as err:
                raise ArchonError(f"Failed to generate checksum: {err}")

    async def post_process(self, fdata: FetchDataDict):
        """Custom post-processing.

        This routine can be overridden to perform custom post-processing of the
        fetched data. It is called with the data, header, and other metadata for
        each CCD. It must modify the data in place and return ``None``.

        Parameters
        ----------
        fdata
            A dictionary of fetched data with the ``data`` array, a ``header``
            dictionary, the ``controller`` and ``ccd`` name, and the ``filename``
            to which the data will be saved.

        """

        return

    async def build_base_header(
        self,
        controller: ArchonController,
        ccd_name: str,
    ) -> dict[str, list]:
        """Returns the basic header of the FITS file."""

        assert self.command.actor and self.expose_data

        expose_data = self.expose_data
        assert expose_data.end_time is not None

        header: dict[str, list] = {}

        # Basic header
        header["V_ARCHON"] = [__version__, ""]
        header["FILENAME"] = ["", "File basename"]  # Will be filled out later
        header["EXPOSURE"] = [None, "Exposure number"]  # Will be filled out later
        header["SPEC"] = [controller.name, "Spectrograph name"]
        header["OBSERVAT"] = [self.command.actor.observatory, "Observatory"]
        header["OBSTIME"] = [expose_data.start_time.isot, "Start of the observation"]
        header["MJD"] = [int(expose_data.start_time.mjd), "Modified Julian Date"]
        header["EXPTIME"] = [expose_data.exposure_time, "Exposure time"]
        header["DARKTIME"] = [expose_data.exposure_time, "Dark time"]
        header["IMAGETYP"] = [expose_data.flavour, "Image type"]
        header["INTSTART"] = [expose_data.start_time.isot, "Start of the integration"]
        header["INTEND"] = [expose_data.end_time.isot, "End of the integration"]

        header["CCD"] = [ccd_name, "CCD name"]

        controller_config = self.config[f"controllers.{controller.name}"]
        if controller_config is None:  # pragma: no cover
            self.command.warning(text="Cannot retrieve controller information.")
            controller_config = Configuration(
                {
                    "detectors": {ccd_name: {}},
                    "parameters": {},
                }
            )

        ccd_config = controller_config[f"detectors.{ccd_name}"]

        ccdid = ccd_config.get("serial", "?")
        ccdtype = ccd_config.get("type", "?")
        gain = ccd_config.get("gain", "?")
        readnoise = ccd_config.get("readnoise", "?")

        header["CCDID"] = [ccdid, "Unique identifier of the CCD"]
        header["CCDTYPE"] = [ccdtype, "CCD type"]

        if isinstance(gain, (list, tuple)):
            for channel_idx in range(len(gain)):
                header[f"GAIN{channel_idx+1}"] = [
                    gain[channel_idx],
                    f"CCD gain AD{channel_idx+1} [e-/ADU]",
                ]
        else:
            header["GAIN"] = [gain, "CCD gain [e-/ADU]"]

        if isinstance(readnoise, (list, tuple)):
            for channel_idx in range(len(readnoise)):
                header[f"RDNOISE{channel_idx+1}"] = [
                    readnoise[channel_idx],
                    f"CCD read noise AD{channel_idx+1} [e-]",
                ]
        else:
            header["RDNOISE"] = [readnoise, "CCD read noise [e-]"]

        window_params = expose_data.window_params
        hbin = window_params.get("hbin", 1)
        vbin = window_params.get("vbin", 1)
        header["CCDSUM"] = [f"{hbin} {vbin}", "Horizontal and vertical binning"]

        # Archon information.
        try:
            system_data = await controller.get_system()
            header["ARCHBACK"] = [system_data["backplane_id"], "Archon backplane ID"]
            header["ARCHBVER"] = [
                system_data["backplane_version"],
                "Archon backplane version",
            ]
        except Exception as err:
            self.command.warning(text=f"Could not get Archon system information: {err}")

        if controller.acf_file:
            acf = os.path.basename(controller.acf_file)
        elif acf_file := self.config["archon.acf_file"]:
            if isinstance(acf_file, dict):
                acf = acf_file.get(controller.name, "?")
            else:
                acf = acf_file
        else:
            acf = "?"
        header["ARCHACF"] = [acf, "Archon ACF file"]

        # Add keywords specified in the configuration file.

        if isinstance(self.config["header"], dict):
            if hconfig := self.config["header"].copy():
                for kname in hconfig:
                    kconfig = hconfig[kname]
                    kname = kname.upper()

                    params = None
                    comment = ""

                    if "command" in kconfig:
                        hcommand = kconfig["command"]
                        if hcommand.lower() == "status":
                            command_data = await controller.get_device_status()
                        elif hcommand.lower() == "system":
                            command_data = await controller.get_system()
                        else:
                            self.command.warning(text=f"Invalid command {hcommand}.")
                            header[kname] = ["N/A", ""]
                            continue

                        if "detectors" in kconfig:
                            for ccd in kconfig["detectors"]:
                                if ccd != ccd_name:
                                    continue
                                params = kconfig["detectors"][ccd][:]
                        else:
                            params = kconfig.get("value", [])[:]

                        if params:
                            # Replace first element, which is the key in the command
                            # reply with the actual value.
                            params[0] = command_data[params[0]]

                    else:
                        if isinstance(kconfig, (list, tuple)):
                            params = kconfig
                        else:
                            params = kconfig

                    if params:
                        if isinstance(params, str):
                            value = params
                        else:
                            value = params[0]
                            if len(params) > 1:
                                comment = params[1]
                            if len(params) > 2:
                                value = float(numpy.round(value, params[2]))
                        header[kname] = [value, comment]

        # Convert JSON lists to tuples or astropy fails.
        for key in expose_data.header:
            if isinstance(expose_data.header[key], list):
                expose_data.header[key] = list(expose_data.header[key])

        # Copy the extra header and loop over potential keys that match
        # the detector name. If so, add those headers only if the detector
        # name matches the current ccd_name.
        detectors = self.config["controllers"][controller.name]["detectors"]
        extra_header = expose_data.header.copy()
        for detector in detectors:
            detector_header = extra_header.pop(detector, {})
            if detector == ccd_name:
                header.update(detector_header)

        # What remains are extra headers to be added to all the detectors.
        for key, value in extra_header.items():
            if (
                key in header
                and not isinstance(value, (tuple, list))
                and isinstance(header[key], tuple)
            ):
                # Preserve original comment.
                header[key] = [value, header[key][1]]
            else:
                if isinstance(value, (tuple, list)):
                    header[key] = list(value)
                else:
                    header[key] = [value, ""]

        return header

    def _set_exposure_no(
        self,
        controllers: list[ArchonController],
        increase: bool = True,
        seqno: int | None = None,
    ):
        """Gets the exposure number for this exposure."""

        assert self.expose_data

        now = astropy.time.Time.now()
        mjd = get_sjd() if self.config["files.use_sjd"] else int(now.mjd)
        self.expose_data.mjd = mjd

        # Get data directory or create it if it doesn't exist.
        data_dir = pathlib.Path(self.config["files"]["data_dir"])
        if not data_dir.exists():
            data_dir.mkdir(parents=True)

        # We store the next exposure number in a file at the root of the data directory.
        next_exp_file = data_dir / "nextExposureNumber"
        if not next_exp_file.exists():
            self.command.warning(f"{next_exp_file} not found. Creating it.")
            next_exp_file.touch()

        if seqno is None:
            with open(next_exp_file, "r") as fd:
                data = fd.read().strip()
                self.expose_data.exposure_no = int(data) if data != "" else 1
        else:
            self.expose_data.exposure_no = seqno

        # Check that files don't exist.
        for controller in controllers:
            ccds = list(self.config["controllers"][controller.name]["detectors"].keys())
            for ccd in ccds:
                try:
                    self._get_ccd_filepath(controller, ccd)
                except FileExistsError as err:
                    self.fail(f"{err} Check the nextExposureNumber file.")
                    return False

        if increase:
            with open(next_exp_file, "w") as fd:
                fd.write(str(self.expose_data.exposure_no + 1))

        return True

    def _get_ccd_filepath(self, controller: ArchonController, ccd: str):
        """Returns the path for an exposure."""

        assert self.command.actor and self.expose_data

        config = self.actor.config

        data_dir = pathlib.Path(config["files"]["data_dir"])

        mjd_dir = data_dir / str(self.expose_data.mjd)
        mjd_dir.mkdir(parents=True, exist_ok=True)

        path: pathlib.Path = mjd_dir / config["files"]["template"]

        observatory = self.command.actor.observatory.lower()
        hemisphere = "n" if observatory == "apo" else "s"

        file_path = str(path.absolute()).format(
            exposure_no=self.expose_data.exposure_no,
            controller=controller.name,
            observatory=observatory,
            hemisphere=hemisphere,
            ccd=ccd,
        )

        if os.path.exists(file_path):
            raise FileExistsError(f"File {file_path} already exists.")

        return file_path

    @staticmethod
    def _get_ccd_data(
        data: numpy.ndarray,
        controller: ArchonController,
        ccd_name: str,
        controller_info: Dict[str, Any],
    ) -> numpy.ndarray:
        """Retrieves the CCD data from the buffer frame."""

        assert controller.acf_config

        pixels = int(controller.acf_config["CONFIG"]["PIXELCOUNT"])
        lines = int(controller.acf_config["CONFIG"]["LINECOUNT"])

        framemode_int = int(controller.acf_config["CONFIG"]["FRAMEMODE"])
        if framemode_int == 0:
            framemode = "top"
        elif framemode_int == 1:
            framemode = "bottom"
        else:
            framemode = "split"

        taps = controller_info["detectors"][ccd_name]["taps"]
        ccd_index = list(controller_info["detectors"].keys()).index(ccd_name)

        if framemode == "top":
            x0_base = ccd_index * pixels * taps
            x0 = x0_base

            ccd_taps = []
            for _ in range(taps):
                y0 = 0
                y1 = lines
                x1 = x0 + pixels

                ccd_taps.append(data[y0:y1, x0:x1])

                x0 = x1

            if len(ccd_taps) == 1:
                return ccd_taps[0]

            bottom = numpy.hstack(ccd_taps[0 : len(ccd_taps) // 2])
            top = numpy.hstack(ccd_taps[len(ccd_taps) // 2 :])
            ccd_data = numpy.vstack([top[:, ::-1], bottom[::-1, :]])

        elif framemode == "split":
            x0 = ccd_index * pixels * (taps // 2)
            x1 = x0 + pixels * (taps // 2)
            y0 = 0
            y1 = lines * (taps // 2)
            ccd_data = data[y0:y1, x0:x1]

        else:
            raise ValueError(f"Framemode {framemode} is not supported at this time.")

        return ccd_data

    def _check_fitsio(self):
        """Checks if fitsio is installed and needed."""

        write_engine: str = self.actor.config["files"].get("write_engine", "astropy")
        if write_engine == "fitsio":
            try:
                import fitsio  # noqa: F401
            except ImportError:
                raise ImportError(
                    "fitsio is required to use fitsio. You can install "
                    "it with 'pip install fitsio' or 'pip install sdss-archon[fitsio]'."
                )
