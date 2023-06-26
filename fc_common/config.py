# -*- coding: utf-8 -*-
#
# Copyright 2023 NXP
#
# SPDX-License-Identifier: MIT


import os

import yaml


class Config:
    @staticmethod
    def save_cfg(cfg):
        cfg_path = os.path.expanduser(os.environ.get("FC_CFG_PATH", "~/.config"))
        cfg_yaml = os.path.join(cfg_path, "fc.yaml")
        os.makedirs(cfg_path, exist_ok=True)

        with open(cfg_yaml, "w", encoding="utf-8") as f_cfg:
            yaml.dump(cfg, f_cfg)

    @staticmethod
    def load_cfg():
        cfg_path = os.path.expanduser(os.environ.get("FC_CFG_PATH", "~/.config"))
        cfg_yaml = os.path.join(cfg_path, "fc.yaml")

        try:
            with open(cfg_yaml, encoding="utf-8") as f_cfg:
                data = yaml.load(f_cfg.read(), yaml.SafeLoader)
                return data
        except Exception:  # pylint: disable=broad-except
            return {}