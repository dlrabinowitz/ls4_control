#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2021-09-06
# @Filename: test_delegate.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

import os

from typing import Any

import numpy
import pytest
from astropy.io import fits
from pytest_mock import MockerFixture

from clu import Command

from archon.actor.actor import ArchonActor
from archon.actor.delegate import ExposureDelegate
from archon.controller import ControllerStatus as CS
from archon.exceptions import ArchonControllerError, ArchonError


@pytest.mark.parametrize("flavour", ["bias", "dark", "object"])
@pytest.mark.parametrize("write_engine", ["astropy", "fitsio"])
@pytest.mark.parametrize("write_async", [True, False])
@pytest.mark.parametrize("checksum_mode", ["md5", "sha1"])
async def test_delegate_expose(
    delegate: ExposureDelegate,
    flavour: str,
    write_engine: bool,
    write_async: bool,
    checksum_mode: str,
):
    delegate.config["files"]["write_engine"] = write_engine
    delegate.config["files"]["write_async"] = write_async
    delegate.config["checksum"]["mode"] = checksum_mode

    command = Command("", actor=delegate.actor)
    result = await delegate.expose(
        command,
        [delegate.actor.controllers["sp1"]],
        flavour=flavour,
        exposure_time=0.01,
        readout=True,
    )

    assert result

    assert delegate.actor.model and delegate.actor.model["filenames"] is not None

    filename = delegate.actor.model["filenames"].value[0]
    assert os.path.exists(filename)

    hdu: Any = fits.open(filename)
    assert hdu[0].data.shape == (800, 800)
    assert hdu[0].header["CCDTEMP1"] == -110


async def test_delegate_expose_invalid_engine(delegate: ExposureDelegate):
    delegate.config["files"]["write_engine"] = "bad_engine"

    command = Command("", actor=delegate.actor)
    result = await delegate.expose(
        command,
        [delegate.actor.controllers["sp1"]],
        exposure_time=0.01,
        readout=True,
    )

    assert result is False


async def test_delegate_expose_invalid_checksum(delegate: ExposureDelegate):
    delegate.config["checksum"]["mode"] = "bad_engine"

    command = Command("", actor=delegate.actor)
    result = await delegate.expose(
        command,
        [delegate.actor.controllers["sp1"]],
        exposure_time=0.01,
        readout=True,
    )

    assert result is True
    assert command.replies[-2].message["text"].startswith("Invalid checksum")


async def test_delegate_expose_top_mode(delegate: ExposureDelegate, mocker):
    # For framemode=top
    mocker.patch.object(
        delegate.actor.controllers["sp1"],
        "fetch",
        return_value=(numpy.ones((400, 400 * 4 * 3)), 1),
    )

    await delegate.actor.controllers["sp1"].write_line("FRAMEMODE", 0, apply="APPLYCDS")

    command = Command("", actor=delegate.actor)
    result = await delegate.expose(
        command,
        [delegate.actor.controllers["sp1"]],
        flavour="object",
        exposure_time=0.01,
        readout=True,
    )

    assert result

    filename = delegate.actor.model["filenames"].value[0]
    assert os.path.exists(filename)

    hdu: Any = fits.open(filename)
    assert hdu[0].data.shape == (800, 800)
    assert hdu[0].header["CCDTEMP1"] == -110


async def test_delegate_expose_locked(delegate: ExposureDelegate):
    await delegate.lock.acquire()

    command = Command("", actor=delegate.actor)
    result = await delegate.expose(
        command,
        [delegate.actor.controllers["sp1"]],
        flavour="object",
        exposure_time=0.01,
        readout=True,
    )

    assert result is False


async def test_delegate_no_use_shutter(delegate: ExposureDelegate, mocker):
    shutter = mocker.patch.object(delegate, "shutter")

    delegate.use_shutter = False

    command = Command("", actor=delegate.actor)
    result = await delegate.expose(
        command,
        [delegate.actor.controllers["sp1"]],
        flavour="object",
        exposure_time=0.01,
        readout=True,
    )

    assert result is True

    shutter.assert_not_called()


async def test_delegate_fetch_fails(delegate: ExposureDelegate, mocker):
    mocker.patch.object(delegate, "fetch_data", side_effect=ArchonError)

    command = Command("", actor=delegate.actor)
    result = await delegate.expose(
        command,
        [delegate.actor.controllers["sp1"]],
        flavour="object",
        exposure_time=0.01,
        readout=True,
    )

    assert result is False


async def test_delegate_expose_no_exptime(delegate: ExposureDelegate):
    command = Command("", actor=delegate.actor)
    result = await delegate.expose(
        command,
        [delegate.actor.controllers["sp1"]],
        flavour="object",
        exposure_time=None,
        readout=True,
    )

    assert result is False


@pytest.mark.parametrize("status", [CS.EXPOSING, CS.READOUT_PENDING, CS.ERROR])
async def test_delegate_check_expose_fails(delegate: ExposureDelegate, status: CS):
    delegate.actor.controllers["sp1"]._status = status

    command = Command("", actor=delegate.actor)

    result = await delegate.expose(
        command,
        [delegate.actor.controllers["sp1"]],
        flavour="object",
        exposure_time=0.01,
        readout=True,
    )

    assert result is False


async def test_delegate_expose_fails(delegate: ExposureDelegate, mocker):
    mocker.patch.object(
        delegate.actor.controllers["sp1"],
        "expose",
        side_effect=ArchonActor,
    )

    command = Command("", actor=delegate.actor)

    result = await delegate.expose(
        command,
        [delegate.actor.controllers["sp1"]],
        flavour="object",
        exposure_time=1,
        readout=True,
    )

    assert result is False


async def test_delegate_readout_not_locked(delegate: ExposureDelegate):
    command = Command("", actor=delegate.actor)
    result = await delegate.expose(
        command,
        [delegate.actor.controllers["sp1"]],
        flavour="object",
        exposure_time=0.01,
        readout=False,
    )
    assert result is True

    delegate.lock.release()

    result = await delegate.readout(command)
    assert result is False


async def test_delegate_readout_no_expose_data(delegate: ExposureDelegate):
    command = Command("", actor=delegate.actor)
    result = await delegate.expose(
        command,
        [delegate.actor.controllers["sp1"]],
        flavour="object",
        exposure_time=0.01,
        readout=False,
    )
    assert result is True

    delegate.expose_data = None

    result = await delegate.readout(command)
    assert result is False


async def test_delegate_shutter_fails(delegate: ExposureDelegate, mocker):
    mocker.patch.object(delegate, "shutter", return_value=False)

    command = Command("", actor=delegate.actor)
    result = await delegate.expose(
        command,
        [delegate.actor.controllers["sp1"]],
        flavour="object",
        exposure_time=0.01,
        readout=False,
    )
    assert result is False


@pytest.mark.parametrize("window_mode", ["test_mode", "default"])
async def test_delegate_expose_window_mode(delegate: ExposureDelegate, window_mode):
    command = Command("", actor=delegate.actor)
    result = await delegate.expose(
        command,
        [delegate.actor.controllers["sp1"]],
        flavour="object",
        exposure_time=0.01,
        readout=True,
        window_mode=window_mode,
    )

    assert result

    filename = delegate.actor.model["filenames"].value[0]
    hdu = fits.open(filename)

    if window_mode == "test_mode":
        assert hdu[0].data.shape == (100, 100)
    else:
        assert hdu[0].data.shape == (800, 800)


async def test_delegate_expose_bad_window_mode(delegate: ExposureDelegate):
    command = Command("", actor=delegate.actor)
    result = await delegate.expose(
        command,
        [delegate.actor.controllers["sp1"]],
        flavour="object",
        exposure_time=0.01,
        readout=True,
        window_mode="bad_window_mode",
    )

    assert result is False


async def test_delegate_expose_set_window_fails(delegate: ExposureDelegate, mocker):
    mocker.patch.object(
        delegate.actor.controllers["sp1"],
        "set_window",
        side_effect=ArchonControllerError,
    )

    command = Command("", actor=delegate.actor)
    result = await delegate.expose(
        command,
        [delegate.actor.controllers["sp1"]],
        flavour="object",
        exposure_time=0.01,
        readout=True,
    )

    assert result is False


async def test_deletage_post_process(delegate: ExposureDelegate, mocker: MockerFixture):
    async def _post_process(fdata):
        fdata["header"]["TEST"] = 1

    mocker.patch.object(delegate, "post_process", side_effect=_post_process)

    delegate.config["files"]["write_engine"] = "fitsio"

    command = Command("", actor=delegate.actor)
    result = await delegate.expose(
        command,
        [delegate.actor.controllers["sp1"]],
        readout=True,
        flavour="object",
        exposure_time=0.01,
    )

    assert result is True

    filename = delegate.actor.model["filenames"].value[0]
    hdu = fits.open(filename)

    assert hdu[0].header["TEST"] == 1


async def test_delegate_no_fitsio(actor: ArchonActor, mocker: MockerFixture):
    mocker.patch.dict("sys.modules", {"fitsio": None})
    actor.config["files"]["write_engine"] = "fitsio"

    with pytest.raises(ImportError):
        ExposureDelegate(actor)


async def test_delegate_copy_temporary_fail(delegate: ExposureDelegate, mocker):
    mocker.patch("shutil.copyfile", side_effect=ValueError)

    command = Command("", actor=delegate.actor)
    result = await delegate.expose(
        command,
        [delegate.actor.controllers["sp1"]],
        flavour="object",
        exposure_time=0.01,
        readout=True,
    )

    assert result is False


async def test_delegate_write_to_disk_file_exists(delegate: ExposureDelegate, mocker):
    mocker.patch("os.path.exists", return_value=True)

    command = Command("", actor=delegate.actor)
    result = await delegate.expose(
        command,
        [delegate.actor.controllers["sp1"]],
        flavour="object",
        exposure_time=0.01,
        readout=True,
    )

    assert result is False
