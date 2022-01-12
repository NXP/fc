# -*- coding: utf-8 -*-

import os
import sys
import logging

# pylint: disable=too-few-public-methods


class Logger:
    @staticmethod
    def init(fc_path):
        log_path = os.environ.get("FC_CONFIG_PATH", os.path.join(fc_path, "log"))
        log_file = os.path.join(log_path, "run.log")

        if not os.path.exists(log_path):
            os.makedirs(log_path)

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            handlers=[logging.FileHandler(log_file), logging.StreamHandler(sys.stdout)],
        )
