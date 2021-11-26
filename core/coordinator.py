# -*- coding: utf-8 -*-

import asyncio
import logging

from importlib import import_module
from core.config import Config
from core.api_svr import ApiSvr


class Coordinator:
    """
    FC coordinator which used to coordinate status among different frameworks
    """

    def __init__(self):
        self.__framework_plugins = [
            import_module("plugins." + framework).Plugin(
                Config.frameworks_config[framework]
            )
            for framework in Config.registered_frameworks
        ]
        self.__managed_resources_status = {}

        for resource in Config.managed_resources:
            self.__managed_resources_status[resource] = "fc"

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
    def managed_resources(self):
        return Config.managed_resources

    @property
    def managed_resources_status(self):
        return self.__managed_resources_status

    @property
    def framework_instances(self):
        return self.__framework_plugins

    def is_resource_available(self, resource):
        return self.__managed_resources_status.get(resource, "") == "fc"

    def __set_resource_status(self, resource, status):
        self.__managed_resources_status[resource] = status
        logging.info("* %s now belongs to %s", resource, status)

    def return_resource(self, resource):
        self.__set_resource_status(resource, "fc")

    def accept_resource(self, resource, context):
        self.__set_resource_status(resource, context.__module__.split(".")[-1])

    def start(self):
        asyncio.run(self.__action())
