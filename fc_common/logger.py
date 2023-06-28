# -*- coding: utf-8 -*-
#
# Copyright 2021-2023 NXP
#
# SPDX-License-Identifier: MIT


import logging
import os

# pylint: disable=too-few-public-methods


class Logger:
    @staticmethod
    def init(logger_name, fc_path, log_name="run.log", log_type="both"):
        log_path = os.environ.get("FC_CONFIG_PATH", os.path.join(fc_path, "log"))
        log_file = os.path.join(log_path, log_name)

        if not os.path.exists(log_path):
            os.makedirs(log_path)

        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)

        s_handler = logging.StreamHandler()
        f_handler = logging.FileHandler(log_file)

        s_format = logging.Formatter(
            fmt="%(asctime)s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        f_format = logging.Formatter(
            fmt="%(asctime)s %(message)s - [%(name)s:%(filename)s:%(lineno)d]",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        s_handler.setFormatter(s_format)
        f_handler.setFormatter(f_format)

        if log_type == "both":
            logger.addHandler(s_handler)
            logger.addHandler(f_handler)
        elif log_type == "stream_only":
            logger.addHandler(s_handler)
        elif log_type == "file_only":
            logger.addHandler(f_handler)
