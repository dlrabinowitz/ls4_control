# !usr/bin/env python
# -*- coding: utf-8 -*-
#
# Licensed under a 3-clause BSD license.
#
# @Author: Brian Cherinka
# @Date:   2017-12-05 12:01:21
# @Last modified by:   Brian Cherinka
# @Last Modified time: 2017-12-05 12:19:32


import inspect

from archon.controller.maskbits import ControllerStatus


class ArchonError(Exception):
    """A custom core Archon exception"""


class ArchonControllerError(ArchonError):
    """An exception raised by an `.ArchonController`."""

    def __init__(self, message, set_error_status: bool = True):
        import archon.controller

        stack = inspect.stack()
        f_locals = stack[1][0].f_locals

        if "self" in f_locals:
            instance = f_locals["self"]
            if isinstance(instance, archon.controller.ArchonController):
                if set_error_status:
                    instance.update_status(ControllerStatus.ERROR)
                controller_name = instance.name
                if controller_name is None or controller_name == "":
                    controller_name = "unnamed"
            else:
                controller_name = "unnamed"
            super().__init__(f"{controller_name} - {message}")
        else:
            super().__init__(message)


class ArchonWarning(Warning):
    """Base warning for Archon."""


class ArchonUserWarning(UserWarning, ArchonWarning):
    """The primary warning class."""

    pass


class ArchonControllerWarning(ArchonUserWarning):
    """A warning issued by an `.ArchonController`."""

    def __init__(self, message):
        import archon.controller

        stack = inspect.stack()
        f_locals = stack[1][0].f_locals

        if "self" in f_locals:
            class_ = f_locals["self"]
            if isinstance(class_, archon.controller.ArchonController):
                controller_name = f_locals["self"].name
                if controller_name is None or controller_name == "":
                    controller_name = "unnamed"
            else:
                controller_name = "unnamed"
            super().__init__(f"{controller_name} - {message}")
        else:
            super().__init__(f"{message}")
