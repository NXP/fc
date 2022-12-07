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


import asyncio
import logging

from async_lru import alru_cache

from fc_server.core.decorators import (
    check_priority_scheduler,
    check_seize_strategy,
    safe_cache,
)
from fc_server.core.plugin import FCPlugin
from fc_server.plugins.utils.lava import Lava


class Plugin(FCPlugin, Lava):
    """
    Plugin for [lava framework](https://git.lavasoftware.org/lava/lava)
    """

    # pylint: disable=too-many-instance-attributes

    def __init__(self, frameworks_config):
        super().__init__()

        self.schedule_interval = 30  # poll lava job queues every 30 seconds
        accurate_scheduler_criteria = frameworks_config.get(
            "accurate_scheduler_criteria", None
        )
        self.accurate_scheduler_criteria__submitter = []
        if accurate_scheduler_criteria:
            self.accurate_scheduler_criteria__submitter = accurate_scheduler_criteria[
                "submitter"
            ]

        self.scheduler_cache = {}  # cache to avoid busy scheduling
        self.seize_cache = {}  # cache to avoid busy seize
        self.job_tags_cache = {}  # cache to store job tags

    @safe_cache
    def __update_cache(self, cache_name, job_id, value):
        self.__dict__[cache_name][job_id] += value

    async def __reset_possible_resource(self, driver, *possible_resources):
        """
        Maintenance all devices once devices finish scheduling.
        Meanwhile, return resouces which participate LAVA scheduling to FC if device idle.
        """

        # let lava scheduler schedule 90 seconds, then do corresponding cleanup
        await asyncio.sleep(90)

        if not driver.is_default_framework(self):
            await self.lava_maintenance_devices(*possible_resources)

        freed_possible_resources = []

        # check if possible resource still be used by lava
        while True:  # pylint: disable=too-many-nested-blocks
            devices = await self.lava_get_devices()
            if devices:
                used_possible_resources = [
                    device
                    for device in devices
                    if device["hostname"] in possible_resources
                    and device["hostname"] not in freed_possible_resources
                ]

                if len(used_possible_resources) == 0:
                    break

                for info in used_possible_resources:
                    if not info["current_job"]:
                        await driver.return_resource(info["hostname"])
                        freed_possible_resources.append(info["hostname"])

                        # clean cache for returned device
                        for job_id in list(self.scheduler_cache.keys()):
                            if info["hostname"] in self.scheduler_cache[job_id]:
                                del self.scheduler_cache[job_id]
                        for job_id in list(self.seize_cache.keys()):
                            if info["hostname"] in self.seize_cache[job_id]:
                                del self.seize_cache[job_id]
            await asyncio.sleep(60)

    async def __get_job_tags(self, job_id):
        """
        Return job tag info, issue interface call will return None
        """

        job_info = await self.lava_get_job_info(job_id)
        return (job_id, job_info["tags"]) if job_info else None

    async def __get_device_tags(self, device):
        """
        Return device tag info, issue interface call will return None
        """

        device_info = await self.lava_get_device_info(device)
        return (device, device_info["tags"]) if device_info else None

    async def __get_device_info(self, device, clear=False):
        """
        Configureable wrapper of lava_get_device_info to clean cache
        """

        if clear:
            self.__get_cached_device_info.cache_clear()  # pylint: disable=no-member

        return await self.__get_cached_device_info(device)

    @alru_cache(None)
    async def __get_cached_device_info(self, device):
        """
        Cached wrapper of lava_get_device_info
        """

        return await self.lava_get_device_info(device)

    async def __get_device_description(self, device):
        """
        Return device description, issue interface call will return None
        """

        device_info = await self.__get_device_info(device)
        return (
            device_info["description"] if device_info else self.lava_default_description
        )

    async def force_kick_off(self, resource):
        """
        Allow coordinator to seize lava resource
        """

        device_info = await self.lava_get_device_info(resource)

        if not device_info:
            return

        current_job = device_info["current_job"]

        if current_job:
            await self.lava_cancel_job(current_job)

    async def __seize_resource(self, driver, job_id, candidated_non_available_devices):
        """
        Request coordinator to seize low priority resource
        """

        non_available_device_tags_list = await asyncio.gather(
            *[
                self.__get_device_tags(candidated_non_available_device)
                for candidated_non_available_device in candidated_non_available_devices
            ]
        )
        non_available_device_tags_list = filter(
            lambda _: isinstance(_, tuple), non_available_device_tags_list
        )
        non_available_device_tags_dict = dict(non_available_device_tags_list)

        candidated_non_available_resources = []
        for device, tags in non_available_device_tags_dict.items():
            if set(self.job_tags_cache[job_id]).issubset(tags):
                candidated_non_available_resources.append(device)
            else:
                self.__update_cache("seize_cache", job_id, [device])

        if candidated_non_available_resources:
            priority_resources = await driver.coordinate_resources(
                self, job_id, *candidated_non_available_resources
            )
            if priority_resources:
                self.__update_cache("seize_cache", job_id, priority_resources)

    async def default_framework_disconnect(self, resource):
        """
        Default framework should realize this to let FC control the disconnect
        """

        device_info = await self.__get_device_info(resource, clear=True)
        if not device_info or device_info["current_job"]:
            return False, False

        if device_info["health"] == "Maintenance":
            logging.info("%s default in maintenance.", resource)
            return True, False

        if device_info["health"] == "Retired":
            logging.info("%s default in retired.", resource)
            return False, False

        # ask default framework disconnect this resource
        logging.info("Disconnect %s from default framework", resource)
        desc = await self.__get_device_description(resource)
        if not await self.lava_maintenance_devices(
            resource, desc=f"{self.device_description_prefix}{desc}"
        ):
            return False, False

        device_info = await self.__get_device_info(resource, clear=True)
        if not device_info or device_info["current_job"]:
            return False, True

        return True, True

    async def default_framework_connect(self, resource):
        """
        Default framework should realize this to let FC control the connect
        """

        # ask default framework connect this resource
        logging.info("Connect %s to default framework", resource)
        desc = await self.__get_device_description(resource)
        return await self.lava_online_devices(
            resource, desc=desc.split(self.device_description_prefix)[-1]
        )

    async def schedule(
        self, driver
    ):  # pylint: disable=too-many-locals, too-many-branches, too-many-statements
        """
        Monitor LAVA job queue, once have pending jobs, online related devices
        to let LAVA take over these devices
        Coodinator will call this function periodly
        """

        async def schedule_prepare():
            # retire managed resources
            devices_assemble = [device["hostname"] for device in devices]
            retired_managed_resources = list(
                set(driver.managed_resources).difference(set(devices_assemble))
            )

            for retired_managed_resource in retired_managed_resources:
                if (
                    driver.managed_resources_status[retired_managed_resource]
                    != "retired"
                ):
                    driver.retire_resource(retired_managed_resource)

            for managed_resource in driver.managed_resources:
                if (
                    driver.managed_resources_status[managed_resource] == "retired"
                    and managed_resource in devices_assemble
                ):
                    driver.reset_resource(managed_resource)

            # category managed resources
            for device in devices:
                if device["hostname"] in driver.managed_resources and device[
                    "health"
                ] in (
                    ("Maintenance", "Unknown", "Good", "Bad")
                    if not driver.is_default_framework(self)
                    else (
                        ("Unknown", "Good", "Maintenance")
                        if driver.managed_disconnect_resource(device["hostname"])
                        else ("Unknown", "Good")
                    )
                ):
                    if not driver.is_default_framework(self):
                        # yield resource which should assure in maintenance mode
                        if device["health"] in (
                            "Unknown",
                            "Good",
                            "Bad",
                        ) and await driver.is_resource_available(
                            self, device["hostname"]
                        ):
                            yield device["hostname"]

                    # guard behavior: in case there are some unexpected manual online & jobs there
                    if device["current_job"] and await driver.is_resource_available(
                        self, device["hostname"]
                    ):
                        driver.accept_resource(device["hostname"], self)
                        asyncio.create_task(
                            self.__reset_possible_resource(
                                driver, *(device["hostname"],)
                            )
                        )

                    # category devices by devicetypes as LAVA schedule based on devicetypes
                    if await driver.is_resource_available(self, device["hostname"]):
                        category_key = "available"
                    elif driver.is_resource_non_available(device["hostname"]):
                        category_key = "non-available"

                    if device["type"] in managed_resources_category[category_key]:
                        managed_resources_category[category_key][device["type"]].append(
                            device["hostname"]
                        )
                    else:
                        managed_resources_category[category_key][device["type"]] = [
                            device["hostname"]
                        ]

        # category devices
        managed_resources_category = {"available": {}, "non-available": {}}
        devices = await self.lava_get_devices()

        if not devices:
            logging.warning(
                "No device fetched from lava server, delay to next scheduling slot"
            )
            return

        if driver.is_default_framework(self):
            async for _ in schedule_prepare():
                pass
        else:
            await self.lava_maintenance_devices(schedule_prepare())

        # query job queue
        possible_resources = []
        queued_jobs = await self.lava_get_queued_jobs()

        # clean cache to save memory
        queued_jobs_ids = [queued_job["id"] for queued_job in queued_jobs]
        for job_id in list(self.job_tags_cache.keys()):
            if job_id not in queued_jobs_ids:
                del self.job_tags_cache[job_id]

        # get tags for queued jobs
        job_tags_list = await asyncio.gather(
            *[
                self.__get_job_tags(queued_job["id"])
                for queued_job in queued_jobs
                if queued_job["id"] not in self.job_tags_cache
            ]
        )
        job_tags_list = filter(lambda _: isinstance(_, tuple), job_tags_list)
        self.job_tags_cache.update(dict(job_tags_list))

        # get devices suitable for queued jobs
        queued_jobs.reverse()
        for queued_job in queued_jobs:
            job_id = queued_job["id"]

            # delay issue job to next scheduling slot
            if job_id not in self.job_tags_cache:
                logging.warning("Job %s delayed to next scheduling slot", job_id)
                continue

            candidated_available_devices = managed_resources_category["available"].get(
                queued_job["requested_device_type"], []
            )

            candidated_available_resources = []

            if job_id not in self.scheduler_cache:
                self.scheduler_cache[job_id] = []

            available_device_tags_list = await asyncio.gather(
                *[
                    self.__get_device_tags(candidated_available_device)
                    for candidated_available_device in candidated_available_devices
                    if candidated_available_device not in self.scheduler_cache[job_id]
                ]
            )
            available_device_tags_list = filter(
                lambda _: isinstance(_, tuple), available_device_tags_list
            )
            available_device_tags_dict = dict(available_device_tags_list)

            for device, tags in available_device_tags_dict.items():
                if set(self.job_tags_cache[job_id]).issubset(tags):
                    candidated_available_resources.append(device)

                    if driver.is_seized_resource(self, device):
                        driver.clear_seized_job_records(device)

            self.__update_cache(
                "scheduler_cache", job_id, list(available_device_tags_dict.keys())
            )
            possible_resources += candidated_available_resources

            # pylint: disable=cell-var-from-loop
            @check_priority_scheduler(driver)
            @check_seize_strategy(driver, self)
            @safe_cache
            def lava_seize_resource(*_):
                candidated_non_available_devices = [
                    non_available_device
                    for non_available_device in managed_resources_category[
                        "non-available"
                    ].get(queued_job["requested_device_type"], [])
                    if non_available_device not in self.seize_cache[job_id]
                ]

                if (
                    not candidated_available_resources
                    and not driver.is_seized_job(job_id)
                    and candidated_non_available_devices
                ):
                    # no available resource found, try to seize from other framework
                    asyncio.create_task(
                        self.__seize_resource(
                            driver, job_id, candidated_non_available_devices
                        )
                    )

            lava_seize_resource(self, "seize_cache", job_id)

        possible_resources = set(possible_resources)

        # let lava dispatch
        if possible_resources:
            for possible_resource in possible_resources:
                driver.accept_resource(possible_resource, self)

            if not driver.is_default_framework(self):
                logging.info("Online devices to schedule lava jobs.")
                await self.lava_online_devices(*possible_resources)

            # cleanup
            asyncio.create_task(
                self.__reset_possible_resource(driver, *possible_resources)
            )

    async def init(self, driver):
        """
        Generate and return tasks to let fc own specified lava devices correctly
        Called only once when coordinator start
        """

        if driver.is_default_framework(self):
            maintenance_devices = [
                device["hostname"]
                for device in await self.lava_get_devices()
                if device["hostname"] in driver.managed_resources
                and device["health"] in ("Maintenance",)
            ]
            recover_devices = [
                (device, await self.__get_device_description(device))
                for device in maintenance_devices
                if (await self.__get_device_description(device)).startswith(
                    self.device_description_prefix
                )
            ]
            return [
                self.lava_online_devices(
                    device, desc=desc.split(self.device_description_prefix)[-1]
                )
                for device, desc in recover_devices
            ]

        return [
            self.lava_maintenance_devices(device["hostname"])
            for device in await self.lava_get_devices()
            if device["hostname"] in driver.managed_resources
            and device["health"] in ("Unknown", "Good", "Bad")
        ]
