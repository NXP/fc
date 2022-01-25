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
import traceback
import yaml

import fc_server.management.common as _
from fc_server.core import AsyncRunMixin
from fc_server.core.config import Config


class LavaManagement(AsyncRunMixin):  # pylint: disable=too-few-public-methods
    def __init__(self):
        self.managed_resources = Config.managed_resources
        self.lava_identities = Config.frameworks_config["lava"]["identities"]

    async def __lava_recover(self, resource):
        cmd = (
            f"lavacli -i {self.lava_identities} devices update --health GOOD {resource}"
        )
        await self._run_cmd(cmd)

    async def action(self):
        candidate_managed_resources = []

        cmd = f"lavacli -i {self.lava_identities} devices list --yaml"
        _, devices_text, _ = await self._run_cmd(cmd)
        try:
            devices = yaml.load(devices_text, Loader=yaml.FullLoader)
            for device in devices:
                if device["hostname"] in self.managed_resources:
                    if device["health"] not in ("Unknown", "Good"):
                        candidate_managed_resources.append(device["hostname"])
        except yaml.YAMLError:
            logging.error(traceback.format_exc())

        recover_tasks = [
            self.__lava_recover(resource) for resource in candidate_managed_resources
        ]
        await asyncio.gather(*recover_tasks)

        logging.info("Recover lava devices done.")


if __name__ == "__main__":
    asyncio.run(LavaManagement().action())
