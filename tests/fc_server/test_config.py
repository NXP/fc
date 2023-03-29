# -*- coding: utf-8 -*-
#
# Copyright 2023 NXP
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
        assert Config.api_server == {"port": 8600}
