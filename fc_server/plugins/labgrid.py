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
import os
from fc_server.core.decorators import (
    check_priority_scheduler,
    check_seize_strategy,
    safe_cache,
)

from fc_server.core.plugin import FCPlugin
from fc_server.plugins.utils.labgrid import Labgrid


class Plugin(FCPlugin, Labgrid):
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
        await self.labgrid_create_reservation(resource, priority=-100)
        logging.info("* [done] inject guard reservation for %s", resource)

    async def __labgrid_fc_reservation(self, driver, resource):
        # let labgrid coordinator has chance to schedule
        await asyncio.sleep(10)

        logging.info("* [start] inject fc reservation for %s", resource)
        await self.labgrid_create_reservation(resource, priority=100, wait=True)
        await self.labgrid_acquire_place(resource)
        logging.info("* [done] inject fc reservation for %s", resource)

        await driver.return_resource(resource)

    async def __labgrid_init(self, resource):
        """
        Let FC take over by inject special reservation
        """
        reservations = await self.labgrid_get_reservations()
        if reservations:
            for _, v in reservations.items():  # pylint: disable=invalid-name
                if v["filters"]["main"] == f"name={resource}":
                    await self.labgrid_cancel_reservation(v["token"], quiet=True)

        await self.labgrid_release_place(resource, force=True, quiet=True)
        await self.labgrid_create_reservation(
            resource, priority=100, wait=True, timeout=20
        )
        await self.labgrid_acquire_place(resource)

    async def force_kick_off(self, resource):
        """
        Allow coordinator to seize labgrid resource
        """

        token = await self.labgrid_get_place_token(resource)

        if token:
            reservations = await self.labgrid_get_reservations()

            if reservations:
                for reservation in reservations.keys():
                    if reservation == f"Reservation '{token}'":
                        await self.labgrid_cancel_reservation(token)
                        await self.labgrid_release_place(resource, True)
                        break

    async def __seize_resource(self, driver, job_id, candidated_resources):
        """
        Request coordinator to seize low priority resource
        """

        if candidated_resources:
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

            await self.labgrid_cancel_reservation(managed_resources_tokens[resource])
            await self.labgrid_release_place(resource)

            # inject a high priority system reservation to let FC lock the device
            # after normal user finish using the device
            asyncio.create_task(self.__labgrid_fc_reservation(driver, resource))

        # query labgrid reservations
        managed_resources_tokens = {}
        reservations = await self.labgrid_get_reservations()
        if reservations:
            for _, v in reservations.items():  # pylint: disable=invalid-name
                resource = v["filters"]["main"][5:]
                if v["owner"] == "fc/fc" and v["state"] == "acquired":
                    managed_resources_tokens[resource] = v["token"]

            resource_list = []
            for _, v in reservations.items():  # pylint: disable=invalid-name
                resource = v["filters"]["main"][5:]
                if v["owner"] != "fc/fc" and v["state"] == "waiting":
                    if await driver.is_resource_available(self, resource):
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
                await asyncio.gather(
                    *[
                        switch_from_fc_to_labgrid(resource)
                        for resource in set(resource_list)
                    ]
                )

    async def init(self, driver):
        """
        Generate and return tasks to let fc own specified labgrid devices
        This be called only once when coordinator start
        """

        places = await self.labgrid_get_places()
        self.managed_resources = [
            place.strip()
            for place in places.splitlines()
            if place.strip() in driver.managed_resources
        ]

        return [self.__labgrid_init(resource) for resource in self.managed_resources]
