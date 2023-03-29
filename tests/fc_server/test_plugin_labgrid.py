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


import asyncio
from unittest.mock import MagicMock

import pytest

from fc_server.plugins.labgrid import Plugin


@pytest.fixture(name="plugin")
def labgrid_plugin():
    config = {
        "lg_crossbar": "ws://$labgrid_crossbar_ip:20408/ws",
        "priority": 2,
        "seize": False,
    }
    return Plugin(config)


# pylint: disable=protected-access
class TestPluginLabgrid:
    @pytest.mark.asyncio
    async def test_force_kick_off(self, mocker, plugin):
        future = asyncio.Future()
        token = "7GN5HFQOEU"
        future.set_result(token)
        mocker.patch(
            "fc_server.plugins.labgrid.Plugin.labgrid_get_place_token",
            return_value=future,
        )

        future = asyncio.Future()
        ret = {
            "Reservation '7GN5HFQOEU'": {
                "owner": "foo/bar",
                "token": "7GN5HFQOEU",
                "state": "acquired",
                "prio": "100.0",
                "filters": {
                    "main": "name=$resource1",
                },
                "allocations": {
                    "main": "$resource1",
                },
                "created": "2023-03-28 10:27:14.881492",
                "timeout": "2023-03-28 11:20:01.893404",
            }
        }
        future.set_result(ret)
        mocker.patch(
            "fc_server.plugins.labgrid.Plugin.labgrid_get_reservations",
            return_value=future,
        )

        future = asyncio.Future()
        ret = MagicMock()
        future.set_result(ret)
        mocker_labgrid_cancel_reservation = mocker.patch(
            "fc_server.plugins.labgrid.Plugin.labgrid_cancel_reservation",
            return_value=future,
        )

        future = asyncio.Future()
        ret = MagicMock()
        future.set_result(ret)
        mocker_labgrid_release_place = mocker.patch(
            "fc_server.plugins.labgrid.Plugin.labgrid_release_place",
            return_value=future,
        )

        await plugin.force_kick_off("$resource1")
        mocker_labgrid_cancel_reservation.assert_called()
        mocker_labgrid_release_place.assert_called()

    @pytest.mark.asyncio
    async def test_seize_resource(self, mocker, coordinator, plugin):
        future = asyncio.Future()
        future.set_result(MagicMock())
        mock_coordinate_resources = mocker.patch(
            "fc_server.core.coordinator.Coordinator.coordinate_resources",
            return_value=future,
        )

        await plugin._Plugin__seize_resource(coordinator, "foo", ["$resource1"])
        mock_coordinate_resources.assert_called()

    @pytest.mark.asyncio
    async def test_schedule(self, mocker, plugin, coordinator):
        future = asyncio.Future()
        ret = {
            "Reservation '83UF223356'": {
                "owner": "fc/fc",
                "token": "83UF223356",
                "state": "acquired",
                "prio": "100.0",
                "filters": {
                    "main": "name=$resource1",
                },
                "allocations": {
                    "main": "$resource1",
                },
                "created": "2023-03-28 09:27:14.881492",
                "timeout": "2023-03-28 10:20:01.893404",
            },
            "Reservation '7GN5HFQOEU'": {
                "owner": "foo/bar",
                "token": "7GN5HFQOEU",
                "state": "waiting",
                "prio": "0",
                "filters": {
                    "main": "name=$resource1",
                },
                "allocations": {
                    "main": "$resource1",
                },
                "created": "2023-03-28 10:27:14.881492",
                "timeout": "2023-03-28 11:20:01.893404",
            },
        }
        future.set_result(ret)
        mocker.patch(
            "fc_server.plugins.labgrid.Plugin.labgrid_get_reservations",
            return_value=future,
        )

        future = asyncio.Future()
        ret = (True, True)
        future.set_result(ret)
        mocker.patch(
            "fc_server.plugins.lava.Plugin.default_framework_disconnect",
            return_value=future,
        )

        future = asyncio.Future()
        future.set_result(MagicMock())
        mocker.patch(
            "fc_server.plugins.labgrid.Plugin._Plugin__labgrid_guard_reservation",
            return_value=future,
        )
        mocker.patch(
            "fc_server.plugins.labgrid.Plugin.labgrid_cancel_reservation",
            return_value=future,
        )
        mocker.patch(
            "fc_server.plugins.labgrid.Plugin.labgrid_release_place",
            return_value=future,
        )

        async def mocker_labgrid_fc_reservation():
            pass

        mocker_labgrid_fc_reservation = mocker.patch(
            "fc_server.plugins.labgrid.Plugin._Plugin__labgrid_fc_reservation",
            return_value=mocker_labgrid_fc_reservation(),
        )

        await plugin.schedule(coordinator)
        mocker_labgrid_fc_reservation.assert_called()
