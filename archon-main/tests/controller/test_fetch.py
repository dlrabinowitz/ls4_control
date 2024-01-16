#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2021-01-28
# @Filename: test_fetch.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

import numpy
import pytest

from archon.controller.controller import ArchonController
from archon.controller.maskbits import ControllerStatus
from archon.exceptions import ArchonControllerError


@pytest.mark.commands(
    [
        [
            "FRAME",
            [
                "<{cid}WBUF=3 BUF1COMPLETE=1 BUF2COMPLETE=1 BUF3COMPLETE=0 "
                "BUF1TIMESTAMP=0 BUF2TIMESTAMP=10 BUF3TIMESTAMP=5 "
                "BUF1WIDTH=640 BUF1HEIGHT=480 BUF1SAMPLE=0 BUF1BASE=0000000000 "
                "BUF2WIDTH=640 BUF2HEIGHT=480 BUF2SAMPLE=0 BUF2BASE=3221225472 "
            ],
        ],
        ["FETCH", [(b"<{cid}:" + b"0" * 1024) * 600]],
    ]
)
@pytest.mark.parametrize("buffer", [-1, 1])
async def test_fetch(controller: ArchonController, buffer):
    arr = await controller.fetch(buffer)
    assert isinstance(arr, numpy.ndarray)
    assert arr.shape == (480, 640)
    assert arr.dtype == "uint16"


async def test_fetch_bad_buffer(controller: ArchonController):
    with pytest.raises(ArchonControllerError):
        await controller.fetch(5)


@pytest.mark.commands(
    [
        [
            "FRAME",
            [
                "<{cid}WBUF=3 BUF1COMPLETE=0 BUF2COMPLETE=0 BUF3COMPLETE=0 "
                "BUF1TIMESTAMP=0 BUF2TIMESTAMP=10 BUF3TIMESTAMP=5 "
            ],
        ]
    ]
)
async def test_fetch_buffer_not_ready(controller: ArchonController):
    with pytest.raises(ArchonControllerError) as err:
        await controller.fetch(-1)
    assert "There are no buffers ready to be read." in str(err.value)


@pytest.mark.commands(
    [["FRAME", ["<{cid}WBUF=3 BUF1COMPLETE=0 BUF2COMPLETE=1 BUF3COMPLETE=0 "]]]
)
async def test_fetch_buffer_not_complete(controller: ArchonController):
    with pytest.raises(ArchonControllerError) as err:
        await controller.fetch(1)
    assert "Buffer frame 1 cannot be read." in str(err.value)


async def test_fetch_already_fetching(controller: ArchonController):
    controller.update_status(ControllerStatus.FETCHING)

    with pytest.raises(ArchonControllerError):
        await controller.fetch()
