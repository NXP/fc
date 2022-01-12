# -*- coding: utf-8 -*-

import asyncio
import logging

from importlib import import_module
from fc_server.core.api_svr import ApiSvr
from fc_server.core.config import Config
from fc_server.core.decorators import check_priority_scheduler


class Coordinator:
    """
    FC coordinator which used to coordinate status among different frameworks
    """

    def __init__(self):
        self.__framework_plugins = [
            import_module("fc_server.plugins." + framework).Plugin(
                Config.frameworks_config[framework]
            )
            for framework in Config.registered_frameworks
        ]

        self.__framework_priorities = {
            framework: Config.frameworks_config[framework]["priority"]
            for framework in Config.registered_frameworks
        }

        self.__framework_seize_strategies = {
            framework: Config.frameworks_config[framework].get("seize", True)
            for framework in Config.registered_frameworks
        }

        self.__managed_resources_status = {}

        for resource in Config.managed_resources:
            self.__managed_resources_status[resource] = "fc"

        # assure no seize for this job when already a seize for this job there
        self.coordinating_job_records = {}

        logging.info("FC managed resource list:")
        logging.info(Config.managed_resources)

    async def __init_frameworks(self):
        logging.info("Start to init following frameworks:")

        init_tasks = []
        for framework in self.__framework_plugins:
            logging.info("  - %s", framework.__module__)
            init_tasks += await framework.init(self)

        await asyncio.gather(*init_tasks)

        logging.info("Framework coordinator ready.")

    async def __schedule_frameworks(self):
        # loop to schedule different frameworks
        while True:
            for framework in self.__framework_plugins:
                if framework.schedule_tick % framework.schedule_interval == 0:
                    framework.schedule_tick = 0
                    await framework.schedule(self)
                framework.schedule_tick += 1

            await asyncio.sleep(1)

    async def __action(self):
        await self.__init_frameworks()
        await ApiSvr(self).start(Config.api_server["port"])
        await self.__schedule_frameworks()

    @property
    def priority_scheduler(self):
        return Config.priority_scheduler

    @property
    def managed_resources(self):
        return Config.managed_resources

    @property
    def managed_resources_status(self):
        return self.__managed_resources_status

    @property
    def framework_instances(self):
        return self.__framework_plugins

    @property
    def framework_seize_strategies(self):
        return self.__framework_seize_strategies

    def __get_low_priority_frameworks(self, cur_framework):
        """
        Get all frameworks with low priority compared to current framework
        """

        return [
            framework
            for framework in self.__framework_priorities.keys()
            if self.__framework_priorities[framework]
            > self.__framework_priorities[cur_framework]
        ]

    def is_resource_available(self, context, resource):
        return self.__managed_resources_status.get(resource, "") in (
            "fc",
            context.__module__.split(".")[-1] + "_seized",
        )

    def is_resource_non_available(self, resource):
        return (
            self.__managed_resources_status.get(resource, "")
            in Config.registered_frameworks
        )

    @check_priority_scheduler()
    def is_seized_resource(self, context, resource):
        return (
            self.__managed_resources_status.get(resource, "")
            == context.__module__.split(".")[-1] + "_seized"
        )

    def clear_seized_job_records(self, device):
        for job_id in list(self.coordinating_job_records.keys()):
            if device == self.coordinating_job_records[job_id]:
                self.coordinating_job_records.pop(job_id)

    def is_seized_job(self, job_id):
        # pylint: disable=consider-iterating-dictionary
        return job_id in list(self.coordinating_job_records.keys())

    @check_priority_scheduler()
    async def coordinate_resources(self, context, job_id, *candidated_resources):
        """
        Seize resource from low priority framework
        """

        logging.info(
            "Seize resource requirement from %s", context.__module__.split(".")[-1]
        )

        candidated_seized_resources = [
            candidated_resource
            for candidated_resource in candidated_resources
            if self.managed_resources_status[candidated_resource]
            in self.__get_low_priority_frameworks(context.__module__.split(".")[-1])
        ]

        high_priority_resources = list(
            set(candidated_resources).difference(set(candidated_seized_resources))
        )
        low_priority_resources = []

        if candidated_seized_resources:
            candidated_seized_resource = candidated_seized_resources[0]
            self.coordinating_job_records[job_id] = candidated_seized_resource

            # kick off resource
            for framework in self.__framework_plugins:
                if (
                    framework.__module__.split(".")[-1]
                    == self.managed_resources_status[candidated_seized_resource]
                ):
                    self.__set_resource_status(
                        candidated_seized_resource,
                        context.__module__.split(".")[-1] + "_seizing",
                    )
                    logging.info(
                        "Force kick off the resource %s.", candidated_seized_resource
                    )
                    await framework.force_kick_off(candidated_seized_resource)
                    self.__set_resource_status(
                        candidated_seized_resource,
                        context.__module__.split(".")[-1] + "_seized",
                    )
                    break
            low_priority_resources.append(candidated_seized_resource)

        return high_priority_resources + low_priority_resources

    def __set_resource_status(self, resource, status):
        self.__managed_resources_status[resource] = status
        logging.info("* %s now belongs to %s", resource, status)

    def return_resource(self, resource):
        if (
            self.__managed_resources_status.get(resource, "")
            in Config.registered_frameworks
        ):
            self.__set_resource_status(resource, "fc")

    def accept_resource(self, resource, context):
        self.__set_resource_status(resource, context.__module__.split(".")[-1])

    def start(self):
        asyncio.run(self.__action())
