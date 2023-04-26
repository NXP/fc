# -*- coding: utf-8 -*-
#
# Copyright 2023 NXP
#
# SPDX-License-Identifier: MIT


import pytest


@pytest.fixture(autouse=True)
def mocker_command_check(mocker):
    mocker.patch("shutil.which")
