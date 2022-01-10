# -*- coding: utf-8 -*-

import asyncio
import logging

from aiohttp import web


class ApiSvr:
    """
    Rest api server
    """

    def __init__(self, context):
        self.context = context

    async def resource_status(self, request):
        res_type = request.match_info.get("res", "")

        response = {}
        if res_type == "resource":
            labgrid_managed_resources = []
            for framework in self.context.framework_instances:
                if framework.__module__.split(".")[-1] == "labgrid":
                    labgrid_managed_resources = framework.managed_resources
                    break

            resources_status_info = []
            for resource, status in self.context.managed_resources_status.items():
                item = []
                if resource not in labgrid_managed_resources:
                    item.append(resource)
                    item.append(status)
                    item.append("non-debuggable")
                else:
                    item.append(resource)
                    item.append(status)
                resources_status_info.append(item)

            response["rc"] = 0
            response["body"] = resources_status_info
        else:
            response["rc"] = 1

        return web.json_response(response)

    @staticmethod
    async def pong(_):
        return web.Response(text="pong")

    async def start(self, port):
        app = web.Application()
        app.add_routes([web.get("/ping", self.pong)])
        app.add_routes([web.get("/{res}", self.resource_status)])

        app_runner = web.AppRunner(app)
        await app_runner.setup()

        api_interface = "0.0.0.0"
        api_port = port
        loop = asyncio.get_event_loop()
        await loop.create_server(app_runner.server, api_interface, api_port)
        logging.info("Api Server ready at http://%s:%d.", api_interface, api_port)
