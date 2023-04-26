# -*- coding: utf-8 -*-
#
# Copyright 2023 NXP
#
# SPDX-License-Identifier: MIT


from unittest.mock import MagicMock

import pytest

from fc_server.plugins.lava import Plugin


@pytest.fixture(name="plugin")
def lava_plugin():
    config = {"identities": "$lava_identity", "priority": 1, "default": True}
    return Plugin(config)


@pytest.fixture(name="lava_job_info")
def create_lava_job_info():
    job_info = {
        "description": "foo",
        "device": None,
        "device_type": "docker",
        "end_time": None,
        "Health": "Unknown",
        "health_check": False,
        "id": "0",
        "pipeline": True,
        "start_time": None,
        "state": "Submitted",
        "submit_time": "20181101T07:13:06",
        "submitter": "foobar",
        "tags": [],
        "visibility": "Public",
    }
    return job_info


@pytest.fixture(name="lava_device_info")
def create_lava_device_info():
    device_info = {
        "current_job": None,
        "description": "Created automatically by LAVA.",
        "device_type": "docker",
        "has_device_dict": "true",
        "health": "Unknown",
        "health_job": "false",
        "hostname": "$resource1",
        "pipeline": "true",
        "state": "Idle",
        "tags": [],
        "worker": "foobar",
    }
    return device_info


@pytest.fixture(name="lava_device_info_unknown")
def create_lava_device_info_unknown(lava_device_info):
    return lava_device_info


@pytest.fixture(name="lava_device_info_good")
def create_lava_device_info_good(lava_device_info):
    lava_device_info.update({"health": "Good"})
    return lava_device_info


@pytest.fixture(name="lava_device_info_with_job")
def create_lava_device_info_with_job(lava_device_info):
    lava_device_info.update({"current_job": "1"})
    return lava_device_info


# pylint: disable=protected-access
class TestPluginLava:
    def test_update_cache(self, plugin):
        plugin._Plugin__update_cache("scheduler_cache", "0", ["foo"])
        assert plugin.scheduler_cache["0"] == ["foo"]

    @pytest.mark.asyncio
    async def test_get_job_tags(self, asyncio_patch, mocker, plugin, lava_job_info):
        asyncio_patch(
            mocker, "fc_server.plugins.lava.Plugin.lava_get_job_info", lava_job_info
        )
        ret = await plugin._Plugin__get_job_tags("0")
        assert ret == ("0", [])

        asyncio_patch(mocker, "fc_server.plugins.lava.Plugin.lava_get_job_info", None)

        ret = await plugin._Plugin__get_job_tags("0")
        assert ret is None

    @pytest.mark.asyncio
    async def test_get_device_tags(
        self, asyncio_patch, mocker, plugin, lava_device_info_unknown
    ):
        asyncio_patch(
            mocker,
            "fc_server.plugins.lava.Plugin.lava_get_device_info",
            lava_device_info_unknown,
        )
        ret = await plugin._Plugin__get_device_tags("$resource1")
        assert ret == ("$resource1", [])

        asyncio_patch(
            mocker, "fc_server.plugins.lava.Plugin.lava_get_device_info", None
        )
        ret = await plugin._Plugin__get_device_tags("$resource1")
        assert ret is None

    @pytest.mark.asyncio
    async def test_get_device_info(
        self,
        asyncio_patch,
        mocker,
        plugin,
        lava_device_info_unknown,
        lava_device_info_good,
    ):
        asyncio_patch(
            mocker,
            "fc_server.plugins.lava.Plugin.lava_get_device_info",
            lava_device_info_unknown,
        )
        ret = await plugin._Plugin__get_device_info("$resource1")
        assert ret == lava_device_info_unknown

        asyncio_patch(
            mocker,
            "fc_server.plugins.lava.Plugin.lava_get_device_info",
            lava_device_info_good,
        )
        ret = await plugin._Plugin__get_device_info("$resource1", clear=True)
        assert ret == lava_device_info_good

        asyncio_patch(
            mocker,
            "fc_server.plugins.lava.Plugin.lava_get_device_info",
            lava_device_info_unknown,
        )
        ret = await plugin._Plugin__get_device_info("$resource1")
        assert ret == lava_device_info_good

    @pytest.mark.asyncio
    async def test_force_kick_off(
        self, asyncio_patch, mocker, plugin, lava_device_info_with_job
    ):
        asyncio_patch(
            mocker,
            "fc_server.plugins.lava.Plugin.lava_get_device_info",
            lava_device_info_with_job,
        )

        mocker_lava_cancel_job = asyncio_patch(
            mocker, "fc_server.plugins.lava.Plugin.lava_cancel_job", MagicMock()
        )
        await plugin.force_kick_off("$resource1")
        mocker_lava_cancel_job.assert_called_with("1")

    @pytest.mark.asyncio
    async def test_seize_resource(self, asyncio_patch, mocker, coordinator, plugin):
        asyncio_patch(
            mocker,
            "fc_server.plugins.lava.Plugin._Plugin__get_device_tags",
            ("$resource1", []),
        )

        mocker_coordinate_resources = asyncio_patch(
            mocker,
            "fc_server.core.coordinator.Coordinator.coordinate_resources",
            MagicMock(),
        )

        plugin.job_tags_cache["0"] = []

        await plugin._Plugin__seize_resource(coordinator, "0", ["$resource1"])
        mocker_coordinate_resources.assert_called()

    @pytest.mark.parametrize(
        "device, seize",
        [
            (
                [
                    {
                        "current_job": None,
                        "health": "Unknown",
                        "hostname": "$resource1",
                        "pipeline": True,
                        "state": "Idle",
                        "type": "docker",
                    }
                ],
                False,
            ),
            (
                [
                    {
                        "current_job": "1",
                        "health": "Unknown",
                        "hostname": "$resource1",
                        "pipeline": True,
                        "state": "Running",
                        "type": "docker",
                    }
                ],
                True,
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_schedule(
        self, asyncio_patch, mocker, plugin, coordinator, device, seize
    ):
        asyncio_patch(mocker, "fc_server.plugins.lava.Plugin.lava_get_devices", device)

        queued_job_info = [
            {
                "description": "foo",
                "id": "0",
                "requested_device_type": "docker",
                "submitter": "bar",
            }
        ]
        asyncio_patch(
            mocker,
            "fc_server.plugins.lava.Plugin.lava_get_queued_jobs",
            queued_job_info,
        )

        job_info = {
            "description": "foo",
            "device": None,
            "device_type": "docker",
            "end_time": None,
            "Health": "Unknown",
            "health_check": False,
            "id": "0",
            "pipeline": True,
            "start_time": None,
            "state": "Submitted",
            "submit_time": "20181101T07:13:06",
            "submitter": "foobar",
            "tags": [],
            "visibility": "Public",
        }
        asyncio_patch(
            mocker, "fc_server.plugins.lava.Plugin.lava_get_job_info", job_info
        )

        device_tags = ("$resource1", [])
        asyncio_patch(
            mocker,
            "fc_server.plugins.lava.Plugin._Plugin__get_device_tags",
            device_tags,
        )

        async def mocker_coro():
            pass

        mocker.patch(
            "fc_server.plugins.lava.Plugin._Plugin__reset_possible_resource",
            return_value=mocker_coro(),
        )

        async def mocker_seize():
            pass

        mocker_seize = mocker.patch(
            "fc_server.plugins.lava.Plugin._Plugin__seize_resource",
            return_value=mocker_seize(),
        )

        await plugin.schedule(coordinator)
        assert mocker_seize.called == seize
