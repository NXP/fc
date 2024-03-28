# -*- coding: utf-8 -*-
#
# Copyright 2024 NXP
#
# SPDX-License-Identifier: MIT


import os

cfg_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "fc_server", "config")
)
os.environ["FC_SERVER_CFG_PATH"] = cfg_path
