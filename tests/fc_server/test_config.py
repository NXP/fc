# -*- coding: utf-8 -*-
#
# Copyright 2023 NXP
#
# SPDX-License-Identifier: MIT


import pytest

from fc_server.core.config import Config


class TestConfig:
    @pytest.mark.usefixtures("remove_config_path")
    def test_no_config_file(self):
        with pytest.raises(SystemExit):
            Config.parse("")

    def test_normal(self):
        Config.parse("")

        assert Config.raw_managed_resources == {
            "$farm_type": {"$device_type": ["$resource1", "$resource2"]}
        }
        assert Config.registered_frameworks == ["lava", "labgrid"]
        assert Config.frameworks_config == {
            "lava": {"default": True, "identities": "$lava_identity", "priority": 1},
            "labgrid": {
                "lg_crossbar": "ws://$labgrid_crossbar_ip:20408/ws",
                "priority": 2,
                "seize": False,
            },
        }
        assert Config.priority_scheduler
        assert Config.api_server == {"port": 8600, "publish_port": 8600}
