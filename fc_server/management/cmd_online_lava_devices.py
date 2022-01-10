#!/usr/bin/env python3

import asyncio
import logging
import traceback
import yaml

import fc_server.management.common as _
from fc_server.core.config import Config
from fc_server.core.plugin import AsyncRunMixin


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
