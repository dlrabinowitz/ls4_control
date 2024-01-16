#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2021-04-10
# @Filename: test_tools.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

import os
from subprocess import CalledProcessError

import pytest

from archon.tools import gzip_async, subprocess_run_async


async def test_subprocess_run_async():
    stdout = await subprocess_run_async("ls", "/")
    assert isinstance(stdout, str)


async def test_subprocess_run_async_shell():
    stdout = await subprocess_run_async("ls /", shell=True)
    assert isinstance(stdout, str)


async def test_subprocess_run_async_bad_returncode():
    with pytest.raises(CalledProcessError):
        await subprocess_run_async("ls", "doesnotexist")


async def test_gzip(tmp_path):
    file = tmp_path / "test.dat"
    file.touch()

    await gzip_async(file)

    assert os.path.exists(str(file) + ".gz")
    assert not file.exists()


async def test_gzip_file_not_exists():
    with pytest.raises(FileNotFoundError):
        await gzip_async("invalid_file.dat")


async def test_gzip_fails(tmp_path, mocker):
    mocker.patch("archon.tools.subprocess_run_async", side_effect=ValueError)

    file = tmp_path / "test.dat"
    file.touch()

    with pytest.raises(OSError):
        await gzip_async(file)
