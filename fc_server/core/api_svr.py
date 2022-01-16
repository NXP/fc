# -*- coding: utf-8 -*-

import asyncio
import logging

import flatdict
from aiohttp import web
from fc_server.core.config import Config


class ApiSvr:
    """
    Rest api server
    """

    def __init__(self, context):
        self.context = context

    async def resource_status(self, request):  # pylint: disable=too-many-branches
        # get all labgrid managed resources
        labgrid_managed_resources = []
        for framework in self.context.framework_instances:
            if framework.__module__.split(".")[-1] == "labgrid":
                labgrid_managed_resources = framework.managed_resources
                break

        res = request.match_info.get("res", "")

        resources_info = []
        if res:
            item = []
            item.append(res)
            item.append(Config.managed_resources_farm_types.get(res, ""))
            item.append(self.context.managed_resources_status.get(res, ""))
            if res not in labgrid_managed_resources:
                item.append("non-debuggable")
            resources_info.append(item)
        else:
            params = request.rel_url.query
            farm_type = params.get("farmtype", "")
            device_type = params.get("devicetype", "")

            if device_type and farm_type:
                scope = Config.raw_managed_resources.get(farm_type, {}).get(
                    device_type, []
                )
            elif device_type:
                scope = []
                for raw_managed_resource in Config.raw_managed_resources.values():
                    scope += raw_managed_resource.get(device_type, [])
            elif farm_type:
                scope = flatdict.FlatterDict(
                    Config.raw_managed_resources.get(farm_type, {})
                ).values()
            else:
                scope = ["all"]

            for resource, status in self.context.managed_resources_status.items():
                if scope != ["all"] and resource not in scope:
                    continue

                item = []
                item.append(resource)
                item.append(Config.managed_resources_farm_types.get(resource, ""))
                item.append(status)
                if resource not in labgrid_managed_resources:
                    item.append("non-debuggable")
                else:
                    item.append("")
                resources_info.append(item)

        return web.json_response(resources_info)

    @staticmethod
    async def pong(_):
        return web.Response(text="pong")

    async def start(self, port):
        app = web.Application()
        app.add_routes([web.get("/ping", self.pong)])
        app.add_routes([web.get("/resource", self.resource_status)])
        app.add_routes([web.get("/resource/{res}", self.resource_status)])

        app_runner = web.AppRunner(app)
        await app_runner.setup()

        api_interface = "0.0.0.0"
        api_port = port
        loop = asyncio.get_event_loop()
        await loop.create_server(app_runner.server, api_interface, api_port)
        logging.info("Api Server ready at http://%s:%d.", api_interface, api_port)
