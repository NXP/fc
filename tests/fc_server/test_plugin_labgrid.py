# -*- coding: utf-8 -*-
#
# Copyright 2023 NXP
#
# SPDX-License-Identifier: MIT


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
    async def test_force_kick_off(self, asyncio_patch, mocker, plugin):
        token = "7GN5HFQOEU"
        asyncio_patch(
            mocker, "fc_server.plugins.labgrid.Plugin.labgrid_get_place_token", token
        )

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
        asyncio_patch(
            mocker, "fc_server.plugins.labgrid.Plugin.labgrid_get_reservations", ret
        )

        mocker_labgrid_cancel_reservation = asyncio_patch(
            mocker,
            "fc_server.plugins.labgrid.Plugin.labgrid_cancel_reservation",
            MagicMock(),
        )
        mocker_labgrid_release_place = asyncio_patch(
            mocker,
            "fc_server.plugins.labgrid.Plugin.labgrid_release_place",
            MagicMock(),
        )

        await plugin.force_kick_off("$resource1")
        mocker_labgrid_cancel_reservation.assert_called()
        mocker_labgrid_release_place.assert_called()

    @pytest.mark.asyncio
    async def test_seize_resource(self, asyncio_patch, mocker, coordinator, plugin):
        mocker_coordinate_resources = asyncio_patch(
            mocker,
            "fc_server.core.coordinator.Coordinator.coordinate_resources",
            MagicMock(),
        )
        await plugin._Plugin__seize_resource(coordinator, "foo", ["$resource1"])

        mocker_coordinate_resources.assert_called()

    @pytest.mark.asyncio
    async def test_schedule(self, asyncio_patch, mocker, plugin, coordinator):
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
        asyncio_patch(
            mocker, "fc_server.plugins.labgrid.Plugin.labgrid_get_reservations", ret
        )

        ret = (True, True)
        asyncio_patch(
            mocker, "fc_server.plugins.lava.Plugin.default_framework_disconnect", ret
        )

        asyncio_patch(
            mocker,
            "fc_server.plugins.labgrid.Plugin._Plugin__labgrid_guard_reservation",
            MagicMock(),
        )
        asyncio_patch(
            mocker,
            "fc_server.plugins.labgrid.Plugin.labgrid_cancel_reservation",
            MagicMock(),
        )
        asyncio_patch(
            mocker,
            "fc_server.plugins.labgrid.Plugin.labgrid_release_place",
            MagicMock(),
        )

        async def mocker_labgrid_system_reservation():
            pass

        mocker_labgrid_system_reservation = mocker.patch(
            "fc_server.plugins.labgrid.Plugin._Plugin__labgrid_system_reservation",
            return_value=mocker_labgrid_system_reservation(),
        )

        await plugin.schedule(coordinator)
        mocker_labgrid_system_reservation.assert_called()
