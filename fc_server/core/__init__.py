# -*- coding: utf-8 -*-
#
# Copyright 2021-2023 NXP
#
# SPDX-License-Identifier: MIT


import asyncio
import os

from fc_common.logger import Logger
from fc_server.core.config import Config

fc_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
Logger.init("fc_server", "fc_server.log")
Config.parse(fc_path)


class AsyncRunMixin:  # pylint: disable=too-few-public-methods
    """
    Mixin for async subprocess call
    """

    async def _run_cmd(self, cmd):  # pylint: disable=no-self-use
        proc = await asyncio.create_subprocess_shell(
            cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            print(f"{cmd!r}:\n  - exited with {proc.returncode}")
        if stderr:
            print(f"  - {stderr.decode()}")

        return proc.returncode, stdout.decode(), stderr.decode()
