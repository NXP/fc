# -*- coding: utf-8 -*-
#
# Copyright 2023 NXP
#
# SPDX-License-Identifier: MIT


import asyncio
from unittest.mock import MagicMock

import pytest

from fc_server.plugins.labgrid import Plugin as LabgridPlugin
from fc_server.plugins.lava import Plugin as LavaPlugin


# pylint: disable=protected-access
@pytest.fixture(name="plugins")
def framework_plugins(coordinator):
    return coordinator._Coordinator__framework_plugins


@pytest.fixture(name="lava_plugin")
def get_lava_plugin(plugins):
    return plugins[0]


@pytest.fixture(name="labgrid_plugin")
def get_labgrid_plugin(plugins):
    return plugins[1]


# pylint: disable=protected-access
class TestCoordinator:
    def test_init_coordinator(self, lava_plugin, labgrid_plugin, coordinator):
        assert isinstance(lava_plugin, LavaPlugin)
        assert isinstance(labgrid_plugin, LabgridPlugin)

        assert coordinator._Coordinator__framework_priorities == {
            "lava": 1,
            "labgrid": 2,
        }
        assert coordinator._Coordinator__framework_seize_strategies == {
            "lava": True,
            "labgrid": False,
        }
        assert isinstance(
            coordinator._Coordinator__default_framework_plugin, LavaPlugin
        )

    @pytest.mark.asyncio
    async def test_init_frameworks(self, asyncio_patch, mocker, coordinator):
        ret = [
            {
                "current_job": "null",
                "health": "Unknown",
                "hostname": "docker-01",
                "pipeline": "true",
                "state": "Idle",
                "type": "docker",
            },
            {
                "current_job": "null",
                "health": "Unknown",
                "hostname": "docker-02",
                "pipeline": "true",
                "state": "Idle",
                "type": "docker",
            },
        ]
        asyncio_patch(mocker, "fc_server.plugins.lava.Plugin.lava_get_devices", ret)

        ret = "docker-01\ndocker-02"
        asyncio_patch(
            mocker, "fc_server.plugins.labgrid.Plugin.labgrid_get_places", ret
        )

        mocker_asyncio_gather = asyncio_patch(mocker, "asyncio.gather", MagicMock())

        await coordinator._Coordinator__init_frameworks()

        mocker_asyncio_gather.assert_called_with(*[])

    def test_is_default_framework(self, lava_plugin, labgrid_plugin, coordinator):
        assert coordinator.is_default_framework(lava_plugin)
        assert not coordinator.is_default_framework(labgrid_plugin)

    def test_get_low_priority_frameworks(self, coordinator):
        assert coordinator._Coordinator__get_low_priority_frameworks("lava") == [
            "labgrid"
        ]
        assert coordinator._Coordinator__get_low_priority_frameworks("labgrid") == []

    @pytest.mark.parametrize(
        "patch_ret, expected",
        [
            # disconnect successful from default framework, and maintenanced by fc
            (
                (True, True),
                (True, ["$resource1"], []),
            ),
            # disconnect successful from default framework, but maintenanced by user
            (
                (True, False),
                (True, [], []),
            ),
            # disconnect fail from default framework due to device busy or api failure,
            # but maintenanced by fc due to race condition
            (
                (False, True),
                (False, [], ["$resource1"]),
            ),
            # disconnect fail from default framework due to device busy or api failure,
            # and without maintenance
            (
                (False, False),
                (False, [], []),
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_is_resource_available(
        self,
        asyncio_patch,
        mocker,
        lava_plugin,
        labgrid_plugin,
        coordinator,
        patch_ret,
        expected,
    ):
        assert await coordinator.is_resource_available(lava_plugin, "$resource1")

        asyncio_patch(
            mocker,
            "fc_server.plugins.lava.Plugin.default_framework_disconnect",
            patch_ret,
        )
        assert (
            await coordinator.is_resource_available(labgrid_plugin, "$resource1")
            == expected[0]
        )
        assert (
            coordinator._Coordinator__managed_issue_disconnect_resources == expected[2]
        )

    def test_is_resource_non_available(self, coordinator):
        assert not coordinator.is_resource_non_available("$resource1")

    def test_is_seized_resource(self, lava_plugin, labgrid_plugin, coordinator):
        assert not coordinator.is_seized_resource(lava_plugin, "$resource1")
        assert not coordinator.is_seized_resource(labgrid_plugin, "$resource1")

    def test_is_seized_job(self, coordinator):
        assert not coordinator.is_seized_job(0)

    def test_accept_resource(self, coordinator, lava_plugin):
        coordinator.accept_resource("$resource1", lava_plugin)
        assert coordinator.managed_resources_status["$resource1"] == "lava"

    @pytest.mark.asyncio
    async def test_return_resource(self, coordinator, lava_plugin):
        coordinator.accept_resource("$resource1", lava_plugin)
        await coordinator.return_resource("$resource1")
        assert coordinator.managed_resources_status["$resource1"] == "fc"

    def test_retire_resource(self, coordinator):
        coordinator.retire_resource("$resource1")
        assert coordinator.managed_resources_status["$resource1"] == "retired"

    def test_reset_resource(self, coordinator):
        coordinator.reset_resource("$resource1")
        assert coordinator.managed_resources_status["$resource1"] == "fc"

    @pytest.mark.asyncio
    async def test_coordinate_resources_basic(self, coordinator, lava_plugin):
        assert await coordinator.coordinate_resources(lava_plugin, 0, *[]) == []

        assert await coordinator.coordinate_resources(lava_plugin, 0, "$resource1") == [
            "$resource1"
        ]

    @pytest.mark.asyncio
    async def test_coordinate_resources_seize_from_lava(
        self, asyncio_patch, mocker, coordinator, lava_plugin
    ):
        coordinator.accept_resource("$resource1", lava_plugin)
        mocker_force_kick_off = asyncio_patch(
            mocker, "fc_server.plugins.labgrid.Plugin.force_kick_off", MagicMock()
        )
        assert await coordinator.coordinate_resources(lava_plugin, 0, "$resource1") == [
            "$resource1"
        ]
        mocker_force_kick_off.assert_not_called()

    @pytest.mark.parametrize("seized_resource_awared", [True, False])
    @pytest.mark.asyncio
    async def test_coordinate_resources_seize_from_labgrid(
        self,
        asyncio_patch,
        mocker,
        coordinator,
        lava_plugin,
        labgrid_plugin,
        seized_resource_awared,
    ):
        coordinator.accept_resource("$resource1", labgrid_plugin)

        mocker_force_kick_off = asyncio_patch(
            mocker, "fc_server.plugins.labgrid.Plugin.force_kick_off", MagicMock()
        )

        mocker_reset_resource = asyncio_patch(
            mocker, "fc_server.core.coordinator.Coordinator.reset_resource", None
        )
        native_sleep = asyncio.sleep
        if not seized_resource_awared:
            asyncio_patch(mocker, "asyncio.sleep", MagicMock())

        assert await coordinator.coordinate_resources(lava_plugin, 0, "$resource1") == [
            "$resource1"
        ]

        if seized_resource_awared:
            coordinator.accept_resource("$resource1", get_lava_plugin)
        await native_sleep(0)

        mocker_force_kick_off.assert_called_with("$resource1")
        assert mocker_reset_resource.called == (not seized_resource_awared)
