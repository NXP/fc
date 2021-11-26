# -*- coding: utf-8 -*-

import os
import logging
import logging.config

# pylint: disable=too-few-public-methods


class Logger:
    @staticmethod
    def init(fc_path):
        log_path = os.path.join(fc_path, "log")
        log_file = os.path.join(log_path, "run.log")
        log_conf = os.path.join(fc_path, "core", "data", "logger.conf")

        if not os.path.exists(log_path):
            os.makedirs(log_path)

        logging.getLogger("asyncio").setLevel(logging.WARNING)
        logging.config.fileConfig(log_conf, defaults=dict(log_file=log_file))
