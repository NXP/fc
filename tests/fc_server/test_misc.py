# -*- coding: utf-8 -*-
#
# Copyright 2023 NXP
#
# SPDX-License-Identifier: MIT


import pytest

from fc_server.core import AsyncRunMixin


# pylint: disable=protected-access
@pytest.mark.parametrize("cmd, ret", [("echo fc", 0), ("echo1 fc", 127)])
class TestAsyncRunMixin:
    @pytest.mark.asyncio
    async def test_run_cmd(self, cmd, ret):
        exit_code = await AsyncRunMixin()._run_cmd(cmd)
        assert exit_code[0] == ret
