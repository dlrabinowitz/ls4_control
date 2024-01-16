#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2021-01-23
# @Filename: test_get_system.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

import pytest

from archon.controller.controller import ArchonController
from archon.controller.maskbits import ModType
from archon.exceptions import ArchonControllerError


@pytest.mark.commands([["SYSTEM", ["<{cid}KEY1=1 KEY2=2"]]])
async def test_get_system(controller: ArchonController):
    system = await controller.get_system()
    assert isinstance(system, dict)
    assert len(system) == 2
    assert system["key1"] == "1"


@pytest.mark.commands([["SYSTEM", ["<{cid}MOD1_TYPE=1"]]])
async def test_get_system_modtype(controller: ArchonController):
    system = await controller.get_system()
    assert isinstance(system, dict)
    assert len(system) == 2
    assert system["mod1_type"] == "1"
    assert system["mod1_name"] == ModType(1).name


@pytest.mark.commands([["SYSTEM", ["?{cid}"]]])
async def test_get_system_error(controller: ArchonController):
    with pytest.raises(ArchonControllerError):
        await controller.get_system()
