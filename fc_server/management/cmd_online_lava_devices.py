#!/usr/bin/env python3
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

import fc_server.management.common as _
from fc_server.core.config import Config
from fc_server.plugins.utils.lava import Lava


class LavaManagement(Lava):
    async def __get_device_description(self, device):
        device_info = await self.lava_get_device_info(device)
        return (
            device_info["description"] if device_info else self.lava_default_description
        )

    async def action(self):
        recover_devices = [
            device["hostname"]
            for device in await self.lava_get_devices()
            if device["hostname"] in Config.managed_resources
            and device["health"] in ("Maintenance",)
        ]

        if Config.default_framework == "lava":
            recover_devices = [
                (device, await self.__get_device_description(device))
                for device in recover_devices
                if (await self.__get_device_description(device)).startswith(
                    self.device_description_prefix
                )
            ]

            await asyncio.gather(
                *[
                    self.lava_online_devices(
                        device, desc=desc.split(self.device_description_prefix)[-1]
                    )
                    for device, desc in recover_devices
                ]
            )
        else:
            await asyncio.gather(
                *[self.lava_online_devices(device) for device in recover_devices]
            )

        logging.info("Recover lava devices done.")


if __name__ == "__main__":
    asyncio.run(LavaManagement().action())
