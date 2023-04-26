# -*- coding: utf-8 -*-
#
# Copyright 2022 NXP
#
# SPDX-License-Identifier: MIT

# pylint: disable=no-member

import asyncio
import logging
import traceback
import types

import yaml

from fc_common import which
from fc_server.core import AsyncRunMixin
from fc_server.core.config import Config
from fc_server.core.decorators import verify_cmd_results

try:
    from functools import singledispatchmethod
except ImportError:
    from singledispatchmethod import singledispatchmethod


class Lava(AsyncRunMixin):
    @which("lavacli", "Use 'pip3 install lavacli' to install lava client please.")
    def __init__(self):
        self.identities = Config.frameworks_config["lava"]["identities"]
        self.device_description_prefix = "[FC]"
        self.lava_default_description = "Created automatically by LAVA."

    @singledispatchmethod
    async def lava_maintenance_devices(
        self, *devices, desc=None
    ):  # pylint: disable=no-self-use, unused-argument
        logging.error("unknown type")

    @lava_maintenance_devices.register(str)
    @verify_cmd_results
    async def _(self, *devices, desc=None):
        cmd_list = []
        for device in devices:
            cmd = (
                f"lavacli -i {self.identities} "
                f"devices update {device} --health MAINTENANCE"
            )
            if desc:
                cmd += f" --description '{desc}'"
            cmd_list.append(cmd)
        results = await asyncio.gather(*[self._run_cmd(cmd) for cmd in cmd_list])

        return results, cmd_list

    @lava_maintenance_devices.register(types.AsyncGeneratorType)
    @verify_cmd_results
    async def _(self, devices, desc=None):
        cmd_list = []
        async for device in devices:
            cmd = (
                f"lavacli -i {self.identities} "
                f"devices update {device} --health MAINTENANCE"
            )
            if desc:
                cmd += f" --description '{desc}'"
            cmd_list.append(cmd)
        results = await asyncio.gather(*[self._run_cmd(cmd) for cmd in cmd_list])

        return results, cmd_list

    @verify_cmd_results
    async def lava_online_devices(self, *devices, desc=None):
        cmd_list = []
        for device in devices:
            cmd = (
                f"lavacli -i {self.identities} "
                f"devices update {device} --health GOOD"
            )
            if desc:
                cmd += f" --description '{desc}'"
            cmd_list.append(cmd)
        results = await asyncio.gather(*[self._run_cmd(cmd) for cmd in cmd_list])

        return results, cmd_list

    async def lava_get_queued_jobs(self):
        """
        LAVA limit at most 100 jobs return for api call
        """

        queued_jobs = []
        seq = 0

        while True:
            cmd_list = []
            batch_num = 5
            jobs_per_batch = 100
            for cnt in range(batch_num):
                cmd = (
                    f"lavacli -i {self.identities} jobs queue "
                    f"--start={batch_num * jobs_per_batch * seq + cnt * jobs_per_batch} "
                    f"--limit={jobs_per_batch} --yaml"
                )
                cmd_list.append(cmd)

            queued_jobs_infos = await asyncio.gather(
                *[self._run_cmd(cmd) for cmd in cmd_list]
            )

            one_batch_queued_jobs = []
            for queued_jobs_info in queued_jobs_infos:
                try:
                    one_batch_queued_jobs += yaml.load(
                        queued_jobs_info[1], Loader=yaml.FullLoader
                    )
                except yaml.YAMLError:
                    logging.error(traceback.format_exc())

            queued_jobs += one_batch_queued_jobs

            if len(one_batch_queued_jobs) < batch_num * jobs_per_batch:
                break

            seq += 1

        return queued_jobs

    async def lava_get_job_info(self, job_id):
        cmd = f"lavacli -i {self.identities} jobs show {job_id} --yaml"
        _, job_info_text, _ = await self._run_cmd(cmd)

        try:
            job_info = yaml.load(job_info_text, Loader=yaml.FullLoader)
        except yaml.YAMLError:
            logging.error(traceback.format_exc())
            return

        return job_info

    async def lava_get_device_info(self, device):
        cmd = f"lavacli -i {self.identities} devices show {device} --yaml"
        _, device_info_text, _ = await self._run_cmd(cmd)

        try:
            device_info = yaml.load(device_info_text, Loader=yaml.FullLoader)
        except yaml.YAMLError:
            logging.error(traceback.format_exc())
            return

        return device_info

    async def lava_get_devices(self):
        cmd = f"lavacli -i {self.identities} devices list --yaml"
        _, devices_text, _ = await self._run_cmd(cmd)

        try:
            devices = yaml.load(devices_text, Loader=yaml.FullLoader)
        except yaml.YAMLError:
            logging.error(traceback.format_exc())
            return []

        return devices

    async def lava_cancel_job(self, job_id):
        cmd = f"lavacli -i {self.identities} jobs cancel {job_id}"
        await self._run_cmd(cmd)
