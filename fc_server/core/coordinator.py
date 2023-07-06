# -*- coding: utf-8 -*-
#
# Copyright 2021-2023 NXP
#
# SPDX-License-Identifier: MIT


import asyncio
import logging
import sys
from importlib import import_module

from fc_server.core.api_svr import ApiSvr
from fc_server.core.config import Config
from fc_server.core.decorators import check_priority_scheduler
from fc_server_daemon.server_daemon import ServerDaemon


class Coordinator:
    """
    FC coordinator which used to coordinate status among different frameworks
    """

    # pylint: disable=too-many-instance-attributes

    def __init__(self):
        self.logger = logging.getLogger("fc_server")

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

        if Config.default_framework:
            self.logger.info("Default framework: %s", Config.default_framework)
            for framework in self.__framework_plugins:
                if framework.__module__.split(".")[-1] == Config.default_framework:
                    self.__default_framework_plugin = framework
                    if not hasattr(
                        self.__default_framework_plugin, "default_framework_disconnect"
                    ) or not hasattr(
                        self.__default_framework_plugin, "default_framework_connect"
                    ):
                        self.logger.fatal(
                            "Fatal: specified default framework doesn't realize next interfaces:"
                        )
                        self.logger.fatal("  - default_framework_disconnect")
                        self.logger.fatal("  - default_framework_connect")
                        sys.exit(1)
                    break

        self.__managed_resources_status = {}
        self.__managed_disconnect_resources = []
        self.__managed_issue_disconnect_resources = []

        for resource in Config.managed_resources:
            self.__managed_resources_status[resource] = "fc"

        # assure no seize for this job when already a seize for this job there
        self.coordinating_job_records = {}

        # record timeout task for seized status
        self.seized_status_timeout_records = {}

        self.logger.info("FC managed resource list:")
        self.logger.info(Config.managed_resources)

    async def __init_frameworks(self):
        self.logger.info("Start to init following frameworks:")

        init_tasks = []
        for framework in self.__framework_plugins:
            self.logger.info("  - %s", framework.__module__)
            init_tasks += await framework.init(self)

        await asyncio.gather(*init_tasks)

        self.logger.info("Framework coordinator ready.")

    async def __managed_issue_resources_connect(self):
        for resource in self.__managed_issue_disconnect_resources:
            if await self.__default_framework_plugin.default_framework_connect(
                resource
            ):
                self.__managed_issue_disconnect_resources.remove(resource)

    async def __schedule_frameworks(self):
        while True:
            # connect all resources which disconnect by fc but previously not successful connect
            await self.__managed_issue_resources_connect()

            # schedule different frameworks
            for framework in self.__framework_plugins:
                if framework.schedule_tick % framework.schedule_interval == 0:
                    framework.schedule_tick = 0
                    await framework.schedule(self)
                framework.schedule_tick += 1

            await asyncio.sleep(1)

    async def __action(self):
        await self.__init_frameworks()
        await ApiSvr(self).start(**Config.api_server)
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

    def managed_disconnect_resource(self, resource):
        return resource in self.__managed_disconnect_resources

    def is_default_framework(self, context):  # pylint: disable=no-self-use
        return context.__module__.split(".")[-1] == Config.default_framework

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

    async def is_resource_available(self, context, resource):
        if self.__managed_resources_status.get(resource, "") == "fc":
            if Config.default_framework:
                if context.__module__.split(".")[-1] == Config.default_framework:
                    return True

                (
                    disconnect_success,
                    maintenance_by_fc,
                ) = await self.__default_framework_plugin.default_framework_disconnect(
                    resource
                )

                if maintenance_by_fc:
                    if disconnect_success:
                        self.__managed_disconnect_resources.append(resource)
                    else:
                        # delay default framework connect if api call failure
                        self.__managed_issue_disconnect_resources.append(resource)
                return disconnect_success

            return True

        if (
            self.__managed_resources_status.get(resource, "")
            == context.__module__.split(".")[-1] + "_seized"
        ):
            return True

        return False

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

    async def __seized_status_timeout(self, resource):
        await asyncio.sleep(90)
        self.logger.info("* %s seized status be reset to fc due to timeout", resource)
        self.reset_resource(resource)

    @check_priority_scheduler()
    async def coordinate_resources(self, context, job_id, *candidated_resources):
        """
        Seize resource from low priority framework
        """

        if not candidated_resources:
            return []

        self.logger.info(
            "[start] seize resource requirement from %s for %s",
            context.__module__.split(".")[-1],
            job_id,
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
                    self.logger.info(
                        "Force kick off the resource %s.", candidated_seized_resource
                    )
                    await framework.force_kick_off(candidated_seized_resource)
                    self.__set_resource_status(
                        candidated_seized_resource,
                        context.__module__.split(".")[-1] + "_seized",
                    )

                    # timeout for seized status
                    timeout_task = asyncio.create_task(
                        self.__seized_status_timeout(candidated_seized_resource)
                    )
                    self.seized_status_timeout_records[
                        candidated_seized_resource
                    ] = timeout_task

                    break
            low_priority_resources.append(candidated_seized_resource)

        self.logger.info(
            "[done] seize resource requirement from %s for %s",
            context.__module__.split(".")[-1],
            job_id,
        )

        return high_priority_resources + low_priority_resources

    def __set_resource_status(self, resource, status):
        self.__managed_resources_status[resource] = status
        self.logger.info("* %s now belongs to %s", resource, status)

    async def return_resource(self, resource):
        if (
            self.__managed_resources_status.get(resource, "")
            in Config.registered_frameworks
        ):
            self.__set_resource_status(resource, "fc")

        if Config.default_framework and resource in self.__managed_disconnect_resources:
            # restore default framework resource status
            self.__managed_disconnect_resources.remove(resource)
            if not await self.__default_framework_plugin.default_framework_connect(
                resource
            ):
                # delay default framework connect for this resource if connect api call failure
                self.__managed_issue_disconnect_resources.append(resource)

    def accept_resource(self, resource, context):
        # cancel seized status timeout task if this resource is seized from others
        if resource in self.seized_status_timeout_records:
            timeout_task = self.seized_status_timeout_records.pop(resource)
            timeout_task.cancel()

        self.__set_resource_status(resource, context.__module__.split(".")[-1])

    def retire_resource(self, resource):
        self.__set_resource_status(resource, "retired")

    def reset_resource(self, resource):
        self.__set_resource_status(resource, "fc")

    def start(self):
        if Config.cluster["enable"]:
            daemon_paras = {
                "etcd": Config.cluster["etcd"],
                "instance_name": Config.cluster["instance_name"],
                "fc": f"http://{Config.api_server['ip']}:{Config.api_server['publish_port']}",
                "lg": Config.frameworks_config["labgrid"]["lg_crossbar"],
                "devices": Config.managed_resources,
            }
            ServerDaemon(daemon_paras).run()

        asyncio.run(self.__action())
