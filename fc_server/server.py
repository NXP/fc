#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2021-2023 NXP
#
# SPDX-License-Identifier: MIT


import logging

from fc_common.version import get_runtime_version
from fc_server.core.coordinator import Coordinator


def main():
    product_text = r"""
______                                           _    _____                     _ _             _
|  ___|                                         | |  /  __ \                   | (_)           | |
| |_ _ __ __ _ _ __ ___   _____      _____  _ __| | _| /  \/ ___   ___  _ __ __| |_ _ __   __ _| |_ ___  _ __
|  _| '__/ _` | '_ ` _ \ / _ \ \ /\ / / _ \| '__| |/ / |    / _ \ / _ \| '__/ _` | | '_ \ / _` | __/ _ \| '__|
| | | | | (_| | | | | | |  __/\ V  V / (_) | |  |   <| \__/\ (_) | (_) | | | (_| | | | | | (_| | || (_) | |
\_| |_|  \__,_|_| |_| |_|\___| \_/\_/ \___/|_|  |_|\_\\____/\___/ \___/|_|  \__,_|_|_| |_|\__,_|\__\___/|_|
    """
    logger = logging.getLogger("fc_server")
    logger.info(product_text)
    logger.info("VERSION: %s", get_runtime_version("fc-server"))

    Coordinator().start()


if __name__ == "__main__":
    main()
