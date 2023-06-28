# -*- coding: utf-8 -*-
#
# Copyright 2023 NXP
#
# SPDX-License-Identifier: MIT


import asyncio
import os
import sys

import pytest

cfg_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "config"))
os.environ["FC_SERVER_CFG_PATH"] = cfg_path

# pylint: disable=wrong-import-position
from fc_server.core.coordinator import Coordinator


@pytest.fixture
def remove_config_path():
    del os.environ["FC_SERVER_CFG_PATH"]
    yield
    os.environ["FC_SERVER_CFG_PATH"] = cfg_path


@pytest.fixture
def coordinator():
    return Coordinator()


@pytest.fixture
def asyncio_patch():
    def _asyncio_patch(mocker, target, result):
        if sys.version_info >= (3, 8):
            from unittest.mock import (  # pylint: disable=import-outside-toplevel
                AsyncMock,
            )

            async_mock = AsyncMock(return_value=result)
            return mocker.patch(target, side_effect=async_mock)

        future = asyncio.Future()
        future.set_result(result)
        return mocker.patch(target, return_value=future)

    return _asyncio_patch
