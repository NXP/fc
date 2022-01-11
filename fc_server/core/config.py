# -*- coding: utf-8 -*-

import os
import yaml

# pylint: disable=too-few-public-methods


class Config:
    @staticmethod
    def parse(fc_path):
        config_path = os.environ.get("FC_CONFIG_PATH", os.path.join(fc_path, "config"))
        cfg_file = os.path.join(config_path, "cfg.yaml")

        with open(cfg_file, "r", encoding="utf-8") as f:  # pylint: disable=invalid-name
            cfg = yaml.load(f, Loader=yaml.FullLoader)

        Config.managed_resources = cfg["managed_resources"]
        Config.registered_frameworks = cfg["registered_frameworks"]
        Config.frameworks_config = cfg["frameworks_config"]
        Config.priority_scheduler = cfg.get("priority_scheduler", False)
        Config.api_server = cfg["api_server"]
