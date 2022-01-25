# -*- coding: utf-8 -*-
#
# Copyright 2021-2022 NXP
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


import logging
import os
import sys
import flatdict
import yaml

# pylint: disable=too-few-public-methods


class Config:
    @staticmethod
    def parse(fc_path):
        config_path = os.environ.get("FC_CONFIG_PATH", os.path.join(fc_path, "config"))
        cfg_file = os.path.join(config_path, "cfg.yaml")

        try:
            with open(cfg_file, "r", encoding="utf-8") as cfg_handle:
                cfg = yaml.load(cfg_handle, Loader=yaml.FullLoader)
        except FileNotFoundError as error:
            logging.error(error)
            logging.error("Put releated configs in %s", config_path)
            logging.error(
                "Instead, you could also set `FC_CONFIG_PATH` to override the default path."
            )
            sys.exit(1)

        raw_managed_resources = cfg["managed_resources"]
        if isinstance(raw_managed_resources, str):
            if not os.path.isabs(raw_managed_resources):
                raw_managed_resources = os.path.join(config_path, raw_managed_resources)
            try:
                with open(
                    raw_managed_resources, "r", encoding="utf-8"
                ) as resources_handle:
                    raw_managed_resources = yaml.load(
                        resources_handle, Loader=yaml.FullLoader
                    )
            except FileNotFoundError as error:
                logging.error(error)
                sys.exit(1)

        Config.raw_managed_resources = raw_managed_resources

        Config.managed_resources = flatdict.FlatterDict(raw_managed_resources).values()
        Config.managed_resources_farm_types = {}
        for farm_type, raw_managed_resource in raw_managed_resources.items():
            Config.managed_resources_farm_types.update(
                {
                    resource: farm_type
                    for resource in flatdict.FlatterDict(raw_managed_resource).values()
                }
            )

        Config.registered_frameworks = cfg["registered_frameworks"]
        Config.frameworks_config = cfg["frameworks_config"]
        Config.priority_scheduler = cfg.get("priority_scheduler", False)
        Config.api_server = cfg["api_server"]
