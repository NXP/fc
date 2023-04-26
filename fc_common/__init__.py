# -*- coding: utf-8 -*-
#
# Copyright 2023 NXP
#
# SPDX-License-Identifier: MIT


import shutil
import sys
from functools import wraps


def which(exe, hint=""):
    def wrapper(func):
        @wraps(func)
        def decorator(*args):
            if not shutil.which(exe):
                print(f"No command '{exe}' found.")
                if hint:
                    print(hint)
                sys.exit(1)

            func(*args)

        return decorator

    return wrapper
