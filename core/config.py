# -*- coding: utf-8 -*-

import os
import yaml

# pylint: disable=too-few-public-methods


class Config:
    @staticmethod
    def parse(fc_path):
        cfg_file = os.path.join(fc_path, "config", "cfg.yaml")
        with open(cfg_file, "r", encoding="utf-8") as f:  # pylint: disable=invalid-name
            cfg = yaml.load(f, Loader=yaml.FullLoader)

        Config.managed_resources = cfg["managed_resources"]
        Config.registered_frameworks = cfg["registered_frameworks"]
        Config.frameworks_config = cfg["frameworks_config"]
        Config.api_server = cfg["api_server"]
