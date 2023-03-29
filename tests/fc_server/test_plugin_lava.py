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

from fc_server.plugins.lava import Plugin


@pytest.fixture(name="plugin")
def lava_plugin():
    config = {"identities": "$lava_identity", "priority": 1, "default": True}
    return Plugin(config)


@pytest.fixture(name="lava_job")
def create_lava_job():
    future = asyncio.Future()
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
    future.set_result(job_info)
    return future


@pytest.fixture(name="lava_job_failure")
def create_lava_job_failure():
    future = asyncio.Future()
    future.set_result(None)
    return future


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


@pytest.fixture(name="lava_device_unknown")
def create_lava_device_unknown(lava_device_info_unknown, create_future):
    return create_future(lava_device_info_unknown)


@pytest.fixture(name="lava_device_good")
def create_lava_device_good(lava_device_info_good, create_future):
    return create_future(lava_device_info_good)


@pytest.fixture(name="lava_device_failure")
def create_lava_device_failure(create_future):
    return create_future(None)


@pytest.fixture(name="lava_device_with_job")
def create_lava_device_with_job(lava_device_info_with_job, create_future):
    return create_future(lava_device_info_with_job)


# pylint: disable=protected-access
class TestPluginLava:
    def test_update_cache(self, plugin):
        plugin._Plugin__update_cache("scheduler_cache", "0", ["foo"])
        assert plugin.scheduler_cache["0"] == ["foo"]

    @pytest.mark.asyncio
    async def test_get_job_tags(self, mocker, plugin, lava_job, lava_job_failure):
        mocker.patch(
            "fc_server.plugins.lava.Plugin.lava_get_job_info",
            return_value=lava_job,
        )
        ret = await plugin._Plugin__get_job_tags("0")
        assert ret == ("0", [])

        mocker.patch(
            "fc_server.plugins.lava.Plugin.lava_get_job_info",
            return_value=lava_job_failure,
        )
        ret = await plugin._Plugin__get_job_tags("0")
        assert ret is None

    @pytest.mark.asyncio
    async def test_get_device_tags(
        self, mocker, plugin, lava_device_unknown, lava_device_failure
    ):
        mocker.patch(
            "fc_server.plugins.lava.Plugin.lava_get_device_info",
            return_value=lava_device_unknown,
        )
        ret = await plugin._Plugin__get_device_tags("$resource1")
        assert ret == ("$resource1", [])

        mocker.patch(
            "fc_server.plugins.lava.Plugin.lava_get_device_info",
            return_value=lava_device_failure,
        )
        ret = await plugin._Plugin__get_device_tags("$resource1")
        assert ret is None

    @pytest.mark.asyncio
    async def test_get_device_info(
        self,
        mocker,
        plugin,
        lava_device_info_unknown,
        lava_device_unknown,
        lava_device_info_good,
        lava_device_good,
    ):
        mocker.patch(
            "fc_server.plugins.lava.Plugin.lava_get_device_info",
            return_value=lava_device_unknown,
        )
        ret = await plugin._Plugin__get_device_info("$resource1")
        assert ret == lava_device_info_unknown

        mocker.patch(
            "fc_server.plugins.lava.Plugin.lava_get_device_info",
            return_value=lava_device_good,
        )
        ret = await plugin._Plugin__get_device_info("$resource1", clear=True)
        assert ret == lava_device_info_good

        mocker.patch(
            "fc_server.plugins.lava.Plugin.lava_get_device_info",
            return_value=lava_device_unknown,
        )
        ret = await plugin._Plugin__get_device_info("$resource1")
        assert ret == lava_device_info_good

    @pytest.mark.asyncio
    async def test_force_kick_off(self, mocker, plugin, lava_device_with_job):
        mocker.patch(
            "fc_server.plugins.lava.Plugin.lava_get_device_info",
            return_value=lava_device_with_job,
        )

        future = asyncio.Future()
        ret = MagicMock()
        future.set_result(ret)
        mock_lava_cancel_job = mocker.patch(
            "fc_server.plugins.lava.Plugin.lava_cancel_job",
            return_value=future,
        )
        await plugin.force_kick_off("$resource1")
        mock_lava_cancel_job.assert_called_with("1")

    @pytest.mark.asyncio
    async def test_seize_resource(self, mocker, coordinator, plugin):
        future = asyncio.Future()
        future.set_result(("$resource1", []))
        mocker.patch(
            "fc_server.plugins.lava.Plugin._Plugin__get_device_tags",
            return_value=future,
        )

        future2 = asyncio.Future()
        future2.set_result(MagicMock())
        mock_coordinate_resources = mocker.patch(
            "fc_server.core.coordinator.Coordinator.coordinate_resources",
            return_value=future2,
        )

        plugin.job_tags_cache["0"] = []

        await plugin._Plugin__seize_resource(coordinator, "0", ["$resource1"])
        mock_coordinate_resources.assert_called()

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
    async def test_schedule(self, mocker, plugin, coordinator, device, seize):
        future = asyncio.Future()
        future.set_result(device)
        mocker.patch(
            "fc_server.plugins.lava.Plugin.lava_get_devices",
            return_value=future,
        )

        future = asyncio.Future()
        queued_job_info = [
            {
                "description": "foo",
                "id": "0",
                "requested_device_type": "docker",
                "submitter": "bar",
            }
        ]
        future.set_result(queued_job_info)
        mocker.patch(
            "fc_server.plugins.lava.Plugin.lava_get_queued_jobs",
            return_value=future,
        )

        future = asyncio.Future()
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
        future.set_result(job_info)
        mocker.patch(
            "fc_server.plugins.lava.Plugin.lava_get_job_info",
            return_value=future,
        )

        future = asyncio.Future()
        device_tags = ("$resource1", [])
        future.set_result(device_tags)
        mocker.patch(
            "fc_server.plugins.lava.Plugin._Plugin__get_device_tags",
            return_value=future,
        )

        async def mocker_coro():
            pass

        mocker.patch(
            "fc_server.plugins.lava.Plugin._Plugin__reset_possible_resource",
            return_value=mocker_coro(),
        )

        async def mocker_seize():
            pass

        mock_seize = mocker.patch(
            "fc_server.plugins.lava.Plugin._Plugin__seize_resource",
            return_value=mocker_seize(),
        )

        await plugin.schedule(coordinator)
        assert mock_seize.called == seize
