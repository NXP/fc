# -*- coding: utf-8 -*-

import asyncio
import logging
import traceback
import yaml

from fc_server.core.decorators import (
    check_priority_scheduler,
    check_seize_strategy,
    safe_cache,
)
from fc_server.core.plugin import AsyncRunMixin, FCPlugin


class Plugin(FCPlugin, AsyncRunMixin):
    """
    Plugin for [lava framework](https://git.lavasoftware.org/lava/lava)
    """

    def __init__(self, frameworks_config):
        super().__init__()
        self.schedule_interval = 30  # poll lava job queues every 30 seconds
        self.identities = frameworks_config["identities"]  # lavacli identities
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

        for resource in possible_resources:
            logging.info("Maintenance: %s", resource)
            cmd = (
                f"lavacli -i {self.identities} devices update --health MAINTENANCE %s"
                % (resource)
            )
            await self._run_cmd(cmd)

        freed_possible_resources = []

        # check if possible resource still be used by lava
        while True:  # pylint: disable=too-many-nested-blocks
            cmd = f"lavacli -i {self.identities} devices list --yaml"
            _, devices_text, _ = await self._run_cmd(cmd)
            try:
                devices = yaml.load(devices_text, Loader=yaml.FullLoader)
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
                        driver.return_resource(info["hostname"])
                        freed_possible_resources.append(info["hostname"])

                        # clean cache for returned device
                        for job_id in list(self.scheduler_cache.keys()):
                            if info["hostname"] in self.scheduler_cache[job_id]:
                                del self.scheduler_cache[job_id]
                        for job_id in list(self.seize_cache.keys()):
                            if info["hostname"] in self.seize_cache[job_id]:
                                del self.seize_cache[job_id]
            except yaml.YAMLError:
                logging.error(traceback.format_exc())
            await asyncio.sleep(60)

    async def __lava_init(self, resource):
        """
        Let FC take over by maintenance lava device
        """

        cmd = f"lavacli -i {self.identities} devices update --health MAINTENANCE {resource}"
        await self._run_cmd(cmd)

    async def __get_job_tags(self, job_id):
        cmd = f"lavacli -i {self.identities} jobs show {job_id} --yaml"
        _, job_info_text, _ = await self._run_cmd(cmd)

        job_info = yaml.load(job_info_text, Loader=yaml.FullLoader)
        return job_id, job_info["tags"]

    async def __get_device_tags(self, device):
        cmd = f"lavacli -i {self.identities} devices show {device} --yaml"
        _, device_info_text, _ = await self._run_cmd(cmd)

        device_info = yaml.load(device_info_text, Loader=yaml.FullLoader)
        return device, device_info["tags"]

    async def force_kick_off(self, resource):
        """
        Allow coordinator to seize lava resource
        """

        cmd = f"lavacli -i {self.identities} devices show {resource} --yaml"
        _, device_info_text, _ = await self._run_cmd(cmd)

        device_info = yaml.load(device_info_text, Loader=yaml.FullLoader)
        current_job = device_info["current_job"]

        if current_job:
            cmd = f"lavacli -i {self.identities} jobs cancel {current_job}"
            await self._run_cmd(cmd)

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
        non_available_device_tags_dict = dict(non_available_device_tags_list)

        candidated_non_available_resources = []
        for device, tags in non_available_device_tags_dict.items():
            if set(self.job_tags_cache[job_id]).issubset(tags):
                candidated_non_available_resources.append(device)
            else:
                self.__update_cache("seize_cache", job_id, [device])

        priority_resources = await driver.coordinate_resources(
            self, job_id, *candidated_non_available_resources
        )
        if priority_resources:
            self.__update_cache("seize_cache", job_id, priority_resources)

    async def schedule(
        self, driver
    ):  # pylint: disable=too-many-locals, too-many-branches, too-many-statements
        """
        Monitor LAVA job queue, once have pending jobs, online related devices
        to let LAVA take over these devices
        Coodinator will call this function periodly
        """

        cmd = f"lavacli -i {self.identities} devices list --yaml"
        _, devices_text, _ = await self._run_cmd(cmd)

        try:
            managed_resources_category = {"available": {}, "non-available": {}}
            devices = yaml.load(devices_text, Loader=yaml.FullLoader)

            cmd_list = []
            for device in devices:
                if device["hostname"] in driver.managed_resources and device[
                    "health"
                ] in ("Maintenance", "Unknown", "Good", "Bad"):
                    # assure all managed devices in maintenance mode
                    if (
                        device["health"]
                        in (
                            "Unknown",
                            "Good",
                            "Bad",
                        )
                        and driver.is_resource_available(self, device["hostname"])
                    ):
                        cmd = (
                            f"lavacli -i {self.identities} "
                            f"devices update --health MAINTENANCE {device['hostname']}"
                        )
                        cmd_list.append(cmd)

                    # guard behavior: in case there are some unexpected manual online & jobs there
                    if device["current_job"] and driver.is_resource_available(
                        self, device["hostname"]
                    ):
                        driver.accept_resource(device["hostname"], self)
                        asyncio.create_task(
                            self.__reset_possible_resource(
                                driver, *(device["hostname"],)
                            )
                        )

                    # category devices by devicetypes as LAVA schedule based on devicetypes
                    if driver.is_resource_available(self, device["hostname"]):
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

            await asyncio.gather(*[self._run_cmd(cmd) for cmd in cmd_list])
        except yaml.YAMLError:
            logging.error(traceback.format_exc())

        # query job queue
        possible_resources = []
        cmd = f"lavacli -i {self.identities} jobs queue --limit=1000 --yaml"
        _, queued_jobs_text, _ = await self._run_cmd(cmd)

        try:
            queued_jobs = yaml.load(queued_jobs_text, Loader=yaml.FullLoader)

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
            self.job_tags_cache.update(dict(job_tags_list))

            # get devices suitable for queued jobs
            queued_jobs.reverse()
            for queued_job in queued_jobs:
                candidated_available_devices = managed_resources_category[
                    "available"
                ].get(queued_job["requested_device_type"], [])

                job_id = queued_job["id"]

                candidated_available_resources = []

                if job_id not in self.scheduler_cache:
                    self.scheduler_cache[job_id] = []

                available_device_tags_list = await asyncio.gather(
                    *[
                        self.__get_device_tags(candidated_available_device)
                        for candidated_available_device in candidated_available_devices
                        if candidated_available_device
                        not in self.scheduler_cache[job_id]
                    ]
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
        except yaml.YAMLError:
            logging.error(traceback.format_exc())

        # let lava dispatch
        if possible_resources:
            logging.info("Online devices to schedule lava jobs.")
            for possible_resource in possible_resources:
                driver.accept_resource(possible_resource, self)

            await asyncio.gather(
                *[
                    self._run_cmd(
                        f"lavacli -i {self.identities} "
                        f"devices update --health GOOD {possible_resource}"
                    )
                    for possible_resource in possible_resources
                ]
            )

            # cleanup
            asyncio.create_task(
                self.__reset_possible_resource(driver, *possible_resources)
            )

    async def init(self, driver):
        """
        Generate and return tasks to let fc own specified lava devices
        This be called only once when coordinator start
        """

        candidate_managed_resources = []

        cmd = f"lavacli -i {self.identities} devices list --yaml"
        _, devices_text, _ = await self._run_cmd(cmd)
        try:
            devices = yaml.load(devices_text, Loader=yaml.FullLoader)
            for device in devices:
                if device["hostname"] in driver.managed_resources:
                    if device["health"] in ("Unknown", "Good", "Bad"):
                        candidate_managed_resources.append(device["hostname"])
        except yaml.YAMLError:
            logging.error(traceback.format_exc())

        return [self.__lava_init(resource) for resource in candidate_managed_resources]
