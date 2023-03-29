# -*- coding: utf-8 -*-
#
# Copyright 2023 NXP
#
# The MIT License (MIT)
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.


import asyncio
import os

import pytest

cfg_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "config"))
os.environ["FC_CONFIG_PATH"] = cfg_path

# pylint: disable=wrong-import-position
from fc_server.core.coordinator import Coordinator


@pytest.fixture
def remove_config_path():
    del os.environ["FC_CONFIG_PATH"]
    yield
    os.environ["FC_CONFIG_PATH"] = cfg_path


@pytest.fixture
def coordinator():
    return Coordinator()


@pytest.fixture
def create_future():
    def _create_future(result):
        future = asyncio.Future()
        future.set_result(result)
        return future

    return _create_future
