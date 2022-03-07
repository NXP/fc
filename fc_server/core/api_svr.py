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
from contextlib import suppress
import logging
from string import Template

import flatdict
from aiohttp import web
from fc_server.core import AsyncRunMixin
from fc_server.core.config import Config


class ApiSvr(AsyncRunMixin):
    """
    Rest api server
    """

    def __init__(self, context):
        self.context = context
        self.external_info_tool = Config.api_server.get("external_info_tool", "")

    @staticmethod
    def friendly_status(status):
        with suppress(Exception):
            return Config.frameworks_config[status]["friendly_status"]
        return status

    async def resource_status(
        self, request
    ):  # pylint: disable=too-many-branches, too-many-locals, too-many-statements
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
            item.append(
                ApiSvr.friendly_status(
                    self.context.managed_resources_status.get(res, "")
                )
            )
            if res not in labgrid_managed_resources:
                item.append("non-debuggable")
            else:
                item.append("")

            # fetch external resource info if needed
            if self.external_info_tool:
                fc_resource = res
                fc_farm_type = Config.managed_resources_farm_types.get(res, "")
                template = Template(self.external_info_tool)
                tool_command = template.substitute(
                    {"fc_resource": fc_resource, "fc_farm_type": fc_farm_type}
                )
                ret, info, _ = await self._run_cmd(tool_command)

                if ret == 0:
                    item.append(info)
                else:
                    item.append("NA")

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

            tool_command_list = []
            for resource, status in self.context.managed_resources_status.items():
                if scope != ["all"] and resource not in scope:
                    continue

                item = []
                item.append(resource)
                item.append(Config.managed_resources_farm_types.get(resource, ""))
                item.append(ApiSvr.friendly_status(status))
                if resource not in labgrid_managed_resources:
                    item.append("non-debuggable")
                else:
                    item.append("")

                resources_info.append(item)

                # fetch external resource info if needed
                if self.external_info_tool and device_type:
                    fc_resource = resource
                    fc_farm_type = Config.managed_resources_farm_types.get(resource, "")
                    template = Template(self.external_info_tool)
                    tool_command = template.substitute(
                        {"fc_resource": fc_resource, "fc_farm_type": fc_farm_type}
                    )
                    tool_command_list.append(self._run_cmd(tool_command))

            external_info_list = await asyncio.gather(*tool_command_list)
            for index, value in enumerate(external_info_list):
                if value[0] == 0:
                    resources_info[index].append(value[1])
                else:
                    resources_info[index].append("NA")

        return web.json_response(resources_info)

    @staticmethod
    async def pong(_):
        return web.Response(text="pong")

    async def booking(self, _):
        cmd = "labgrid-client who | grep -v fc"
        _, bookings_text, _ = await self._run_cmd(cmd)

        bookings_text_list = []
        header = True
        anchor = -1
        for booking_text in bookings_text.splitlines():
            if header:
                anchor = booking_text.find("Place")
                bookings_text_list.append(booking_text)
                header = False
                continue

            if booking_text[anchor:].split(" ")[0] in Config.managed_resources:
                bookings_text_list.append(booking_text)

        return web.Response(text="\n".join(bookings_text_list))

    async def start(self, port):
        app = web.Application()
        app.add_routes([web.get("/ping", self.pong)])
        app.add_routes([web.get("/booking", self.booking)])
        app.add_routes([web.get("/resource", self.resource_status)])
        app.add_routes([web.get("/resource/{res}", self.resource_status)])

        app_runner = web.AppRunner(app)
        await app_runner.setup()

        api_interface = "0.0.0.0"
        api_port = port
        loop = asyncio.get_event_loop()
        await loop.create_server(app_runner.server, api_interface, api_port)
        logging.info("Api Server ready at http://%s:%d.", api_interface, api_port)
