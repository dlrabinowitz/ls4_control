#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2021-01-23
# @Filename: test_get_system.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

import pytest

from archon.controller.controller import ArchonController
from archon.exceptions import ArchonControllerError


@pytest.mark.commands([["FRAME", ["<{cid}TIME=FF KEY2=2 BUFF2TIMESTAMP=AF"]]])
async def test_get_frame(controller: ArchonController):
    system = await controller.get_frame()
    assert isinstance(system, dict)
    assert len(system) == 3
    assert system["time"] == 0xFF
    assert system["key2"] == 2
    assert system["buff2timestamp"] == 0xAF


@pytest.mark.commands([["FRAME", ["?{cid}"]]])
async def test_get_frame_fails(controller: ArchonController):
    with pytest.raises(ArchonControllerError):
        await controller.get_frame()
