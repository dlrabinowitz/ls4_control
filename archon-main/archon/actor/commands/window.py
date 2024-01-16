#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2022-04-29
# @Filename: window.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)

from __future__ import annotations

import asyncio

import click

import archon.actor
from archon.controller.controller import ArchonController

from . import parser


__all__ = ["set_window", "get_window"]


@parser.command(name="get-window")
async def get_window(command: archon.actor.ArchonCommandType, controllers):
    """Outputs the current exposure window."""

    if len(controllers) == 0:
        return command.fail(error="No controllers found.")

    controller = list(controllers.values())[0]
    return command.finish(**controller.current_window)


@parser.command(name="set-window")
@click.argument("WINDOW-MODE", required=False, type=str)
@click.option("--lines", type=int, help="Number of lines to read.")
@click.option("--pixels", type=int, help="Number of pixels to read.")
@click.option("--preskiplines", type=int, help="Number of lines to pre-skip.")
@click.option("--postskiplines", type=int, help="Number of lines to post-skip.")
@click.option("--preskippixels", type=int, help="Number of pixels to pre-skip.")
@click.option("--postskippixels", type=int, help="Number of pixels to post-skip.")
@click.option("--overscanlines", type=int, help="Number of overscan lines.")
@click.option("--overscanpixels", type=int, help="Number of overscan pixels.")
@click.option("--hbin", type=int, help="Horizontal binning.")
@click.option("--vbin", type=int, help="Vertical binning.")
async def set_window(
    command: archon.actor.ArchonCommandType,
    controllers: dict[str, ArchonController],
    **win_args,
):
    """Sets the exposure window.

    A WINDOW-MODE can be specified to load a window profile from the configuration
    file. Additional flags will modify the parameters in the window mode. The
    new window settings are always incremental: if a parameter is not defined
    in the window mode or as a specific flag, the current value is kept. To
    reload the default window settings from the ACF file use WINDOW-MODE=default
    or use set-window without arguments.

    """

    window_mode = win_args.pop("window_mode", None)
    win_args = {k: v for k, v in win_args.items() if v is not None}

    if window_mode == "default" or (window_mode is None and win_args == {}):
        await asyncio.gather(*[c.reset_window() for c in controllers.values()])
    else:
        if window_mode is not None:
            config = command.actor.config
            if "window_modes" in config and window_mode in config["window_modes"]:
                mode_params = config["window_modes"][window_mode]
                mode_params.update({k: v for k, v in win_args.items() if v})
                win_args = mode_params
            else:
                return command.fail(error=f"Invalid window mode {window_mode!r}.")

        await asyncio.gather(*[c.set_window(**win_args) for c in controllers.values()])

    controller = list(controllers.values())[0]
    return command.finish(**controller.current_window)
