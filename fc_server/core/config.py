# -*- coding: utf-8 -*-
#
# Copyright 2021-2023 NXP
#
# SPDX-License-Identifier: MIT


import logging
import os
import sys

import flatdict
import yaml

# pylint: disable=too-few-public-methods


class Config:
    logger = logging.getLogger("fc_server")

    @staticmethod
    def parse(fc_path):  # pylint: disable=too-many-statements
        config_path = os.environ.get(
            "FC_SERVER_CFG_PATH", os.path.join(fc_path, "config")
        )
        cfg_file = os.path.join(config_path, "cfg.yaml")

        try:
            with open(cfg_file, "r", encoding="utf-8") as cfg_handle:
                cfg = yaml.load(cfg_handle, Loader=yaml.FullLoader)
        except FileNotFoundError as error:
            Config.logger.error(error)
            Config.logger.error("Put releated configs in %s", config_path)
            Config.logger.error(
                "Instead, you could also set `FC_SERVER_CFG_PATH` to override the default path."
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
                Config.logger.error(error)
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

        cluster = cfg.get("cluster", None)
        if cluster:
            Config.cluster = {}
            Config.cluster["enable"] = cluster.get("enable", False)
            Config.cluster["instance_name"] = cluster.get("instance_name", None)
            Config.cluster["etcd"] = cluster.get("etcd", None)

            if Config.cluster["enable"] and (
                not Config.cluster["instance_name"] or not Config.cluster["etcd"]
            ):
                Config.logger.error(
                    "instance_name & etcd is mandatory when enable cluster feature"
                )
                sys.exit(1)

        Config.registered_frameworks = cfg["registered_frameworks"]
        Config.frameworks_config = cfg["frameworks_config"]
        Config.priority_scheduler = cfg.get("priority_scheduler", False)

        Config.api_server = cfg["api_server"]
        if "port" not in Config.api_server:
            Config.logger.error("port for api_server is mandatory")
            sys.exit(1)
        if "publish_port" not in Config.api_server:
            Config.api_server["publish_port"] = Config.api_server["port"]
        if "ip" not in Config.api_server:
            if cluster and Config.cluster["enable"]:
                Config.logger.error("ip for api_server in cluster mode is mandatory")
                sys.exit(1)

        default_framework_strategies = [
            framework
            for framework in Config.registered_frameworks
            if Config.frameworks_config[framework].get("default", False)
        ]
        default_framework_number = len(default_framework_strategies)
        if default_framework_number > 1:
            Config.logger.fatal(
                "Fatal: at most one default framework could be specifed!"
            )
            sys.exit(1)

        Config.default_framework = (
            None if default_framework_number == 0 else default_framework_strategies[0]
        )
