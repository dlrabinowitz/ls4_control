#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2021-04-06
# @Filename: test_exceptions.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

import warnings

import pytest

from archon.exceptions import ArchonControllerError, ArchonControllerWarning


async def test_archon_controller_error_unnamed(controller):
    controller.name = None

    with pytest.raises(ArchonControllerError) as err:
        await controller.send_command("TEST", command_id=100000000)

    assert "unnamed - " in str(err.value)


async def test_archon_controller_error_no_controller():
    class Test:
        def __init__(self):
            raise ArchonControllerError("test error")

    with pytest.raises(ArchonControllerError) as err:
        Test()

    assert "unnamed - test error" in str(err.value)


async def test_archon_controller_error_no_class():
    with pytest.raises(ArchonControllerError) as err:
        raise ArchonControllerError("test error")

    assert str(err.value) == "test error"


async def test_archon_controller_warning_unnamed(controller):
    controller.name = None

    with pytest.warns(ArchonControllerWarning) as warn:
        await controller.process_message(b"TEST")

    assert "unnamed - " in str(warn[-1].message)


async def test_archon_controller_warning_no_controller():
    class Test:
        def __init__(self):
            warnings.warn("test warning", ArchonControllerWarning)

    with pytest.warns(ArchonControllerWarning) as warn:
        Test()

    assert "unnamed - test warning" in str(warn[-1].message)


async def test_archon_controller_warning_no_class():
    with pytest.warns(ArchonControllerWarning) as warn:
        warnings.warn("test warning", ArchonControllerWarning)

    assert str(warn[-1].message) == "test warning"
