# -*- coding: utf-8 -*-

import asyncio
import logging
import traceback
import yaml

from core.plugin import FCPlugin


class Plugin(FCPlugin):
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

    async def __reset_possible_resource(self, driver, *possible_resources):
        """
        Maintenance all devices once devices finish scheduling.
        Meanwhile, return resouces which participate LAVA scheduling to FC if device idle.
        """

        # let lava scheduler schedule 60 seconds, then do corresponding cleanup
        await asyncio.sleep(60)

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
            _, devices_text, _ = await self._run_cmd(
                f"lavacli -i {self.identities} devices list --yaml"
            )
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
            except yaml.YAMLError:
                logging.error(traceback.format_exc())
            await asyncio.sleep(60)

    async def __lava_init(self, resource):
        """
        Let FC take over by maintenance lava device
        """

        cmd = f"lavacli -i {self.identities} devices update --health MAINTENANCE {resource}"
        await self._run_cmd(cmd)

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
            managed_resources_category = {}
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
                        and driver.is_resource_available(device["hostname"])
                    ):
                        cmd = (
                            f"lavacli -i {self.identities} "
                            f"devices update --health MAINTENANCE {device['hostname']}"
                        )
                        cmd_list.append(cmd)

                    # guard behavior: in case there are some unpexcted manual online & jobs there
                    if device["current_job"] and driver.is_resource_available(
                        device["hostname"]
                    ):
                        driver.accept_resource(device["hostname"], self)
                        asyncio.create_task(
                            self.__reset_possible_resource(
                                driver, *(device["hostname"],)
                            )
                        )

                    # category devices by devicetypes as LAVA schedule based on devicetypes
                    if driver.is_resource_available(device["hostname"]):
                        if device["type"] in managed_resources_category:
                            managed_resources_category[device["type"]].append(
                                device["hostname"]
                            )
                        else:
                            managed_resources_category[device["type"]] = [
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

            # get devices suitable for queued jobs
            for queued_job in queued_jobs:
                candidated_devices = managed_resources_category.get(
                    queued_job["requested_device_type"], []
                )
                candidated_resources = candidated_devices

                submitter = queued_job["submitter"]
                job_id = queued_job["id"]

                if (
                    submitter in self.accurate_scheduler_criteria__submitter
                    or "all" in self.accurate_scheduler_criteria__submitter
                ):
                    cmd = f"lavacli -i {self.identities} jobs show {job_id} --yaml"
                    _, job_info_text, _ = await self._run_cmd(cmd)
                    job_info = yaml.load(job_info_text, Loader=yaml.FullLoader)

                    accurate_devices = []
                    for candidated_device in candidated_devices:
                        cmd = f"lavacli -i dev devices show {candidated_device} --yaml"
                        _, device_info_text, _ = await self._run_cmd(cmd)
                        device_info = yaml.load(
                            device_info_text, Loader=yaml.FullLoader
                        )
                        if set(job_info["tags"]).issubset(device_info["tags"]):
                            accurate_devices.append(candidated_device)

                    candidated_resources = accurate_devices

                if job_id in self.scheduler_cache:
                    for candidated_resource in candidated_resources:
                        # if one resource already be scheduled but not matched,
                        # don't schedule it again to avoid busy scheduling
                        if candidated_resource not in self.scheduler_cache[job_id]:
                            self.scheduler_cache[job_id].append(candidated_resource)
                            possible_resources.append(candidated_resource)
                else:
                    self.scheduler_cache[job_id] = candidated_resources
                    possible_resources += candidated_resources
            possible_resources = set(possible_resources)
        except yaml.YAMLError:
            logging.error(traceback.format_exc())

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
