# -*- coding: utf-8 -*-

import asyncio
import logging
import os
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
    Plugin for [labgrid framework](https://github.com/labgrid-project/labgrid)
    """

    def __init__(self, frameworks_config):
        super().__init__()
        self.schedule_interval = 2  # poll labgrid reserve queues every 2 seconds

        os.environ["LG_CROSSBAR"] = frameworks_config["lg_crossbar"]
        os.environ["LG_HOSTNAME"] = "fc"
        os.environ["LG_USERNAME"] = "fc"

        self.managed_resources = None

        self.seize_cache = {}  # cache to avoid busy seize

    @safe_cache
    def __update_cache(self, cache_name, job_id, value):
        self.__dict__[cache_name][job_id] += value

    async def __labgrid_guard_reservation(self, resource):
        logging.info("* [start] inject guard reservation for %s", resource)

        cmd = f"labgrid-client reserve --prio -100 name={resource}"
        await self._run_cmd(cmd)

        logging.info("* [done] inject guard reservation for %s", resource)

    async def __labgrid_fc_reservation(self, driver, resource):
        # let labgrid coordinator has chance to schedule
        await asyncio.sleep(10)

        logging.info("* [start] inject fc reservation for %s", resource)

        cmd = f"labgrid-client reserve --wait --prio 100 name={resource}"
        await self._run_cmd(cmd)

        cmd = f"labgrid-client -p {resource} acquire"
        await self._run_cmd(cmd)

        logging.info("* [done] inject fc reservation for %s", resource)

        driver.return_resource(resource)

    async def __labgrid_init(self, resource):
        """
        Let FC take over by inject special reservation
        """
        _, reservations_text, _ = await self._run_cmd("labgrid-client reservations")
        try:
            reservations = yaml.load(reservations_text, Loader=yaml.FullLoader)
            if reservations:
                for _, v in reservations.items():  # pylint: disable=invalid-name
                    if v["filters"]["main"] == f"name={resource}":
                        cmd = f"labgrid-client cancel-reservation {v['token']} > /dev/null 2>&1"
                        await self._run_cmd(cmd)
        except yaml.YAMLError:
            logging.error(traceback.format_exc())

        cmd = f"labgrid-client -p {resource} release -k > /dev/null 2>&1"
        await self._run_cmd(cmd)

        cmd = f"timeout 20 labgrid-client reserve --wait --prio 100 name={resource}"
        await self._run_cmd(cmd)

        cmd = f"labgrid-client -p {resource} acquire"
        await self._run_cmd(cmd)

    async def force_kick_off(self, resource):
        """
        Allow coordinator to seize labgrid resource
        """

        cmd = f"labgrid-client -p {resource} show"
        _, place_info_text, _ = await self._run_cmd(cmd)
        place_info_text = place_info_text.decode()

        token = ""
        place_info_lines = place_info_text.splitlines()
        for line in place_info_lines:
            if line.find("reservation") >= 0:
                token = line.split(":")[-1].strip()
                break

        if token:
            cmd = "labgrid-client reservations"
            _, reservations_text, _ = await self._run_cmd(cmd)
            reservations = yaml.load(reservations_text, Loader=yaml.FullLoader)
            for reservation in reservations.keys():
                if reservation == f"Reservation '{token}'":
                    await self._run_cmd(f"labgrid-client cancel-reservation {token}")
                    await self._run_cmd(f"labgrid-client -p {resource} unlock -k")
                    break

    async def __seize_resource(self, driver, job_id, candidated_resources):
        """
        Request coordinator to seize low priority resource
        """

        priority_resources = await driver.coordinate_resources(
            self, job_id, *candidated_resources
        )
        if priority_resources:
            self.__update_cache("seize_cache", job_id, priority_resources)

    async def schedule(self, driver):
        """
        Monitor Labgrid reserve queue, once have pending reservation,
        release current fc acquisition to let normal user acquire the device
        Coodinator will call this function periodly
        """

        async def switch_from_fc_to_labgrid(resource):
            # there is at most 10 seconds gap there if normal user release its acquired device
            # to avoid empty reservation during this period
            # inject a low priority system reservation
            await self.__labgrid_guard_reservation(resource)

            cmd = f"labgrid-client cancel-reservation {managed_resources_tokens[resource]}"
            await self._run_cmd(cmd)
            cmd = f"labgrid-client -p {resource} release"
            await self._run_cmd(cmd)

            # inject a high priority system reservation to let FC lock the device
            # after normal user finish using the device
            asyncio.create_task(self.__labgrid_fc_reservation(driver, resource))

        # query labgrid reservations
        managed_resources_tokens = {}
        cmd = "labgrid-client reservations"
        _, reservations_text, _ = await self._run_cmd(cmd)
        try:  # pylint: disable=too-many-nested-blocks
            reservations = yaml.load(reservations_text, Loader=yaml.FullLoader)
            if reservations:
                for _, v in reservations.items():  # pylint: disable=invalid-name
                    resource = v["filters"]["main"][5:]
                    if v["owner"] == "fc/fc" and v["state"] == "acquired":
                        managed_resources_tokens[resource] = v["token"]

                resource_list = []
                for _, v in reservations.items():  # pylint: disable=invalid-name
                    resource = v["filters"]["main"][5:]
                    if v["owner"] != "fc/fc" and v["state"] == "waiting":
                        if driver.is_resource_available(self, resource):
                            if driver.is_seized_resource(self, resource):
                                driver.clear_seized_job_records(resource)

                            # if has pending reservation not belongs to normal user
                            # meanwhile device currently belongs to fc, accept it
                            driver.accept_resource(resource, self)
                            resource_list.append(resource)
                        else:
                            job_id = v["token"]

                            # pylint: disable=cell-var-from-loop
                            @check_priority_scheduler(driver)
                            @check_seize_strategy(driver, self)
                            @safe_cache
                            def labgrid_seize_resource(*_):
                                candidated_resources = (
                                    []
                                    if resource in self.seize_cache[job_id]
                                    else [resource]
                                )

                                if (
                                    not driver.is_seized_job(job_id)
                                    and candidated_resources
                                ):
                                    # no available resource found, try to seize from other framework
                                    asyncio.create_task(
                                        self.__seize_resource(
                                            driver, job_id, candidated_resources
                                        )
                                    )

                            labgrid_seize_resource(self, "seize_cache", job_id)

                if resource_list:
                    asyncio.gather(
                        *[
                            switch_from_fc_to_labgrid(resource)
                            for resource in set(resource_list)
                        ]
                    )
        except yaml.YAMLError:
            logging.error(traceback.format_exc())

    async def init(self, driver):
        """
        Generate and return tasks to let fc own specified labgrid devices
        This be called only once when coordinator start
        """
        cmd = "labgrid-client p"
        _, places, _ = await self._run_cmd(cmd)
        self.managed_resources = [
            place.strip()
            for place in places.decode().splitlines()
            if place.strip() in driver.managed_resources
        ]

        return [self.__labgrid_init(resource) for resource in self.managed_resources]
