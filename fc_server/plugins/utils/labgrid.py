# -*- coding: utf-8 -*-
#
# Copyright 2022 NXP
#
# SPDX-License-Identifier: MIT


import logging
import traceback

import yaml

from fc_common import which
from fc_server.core import AsyncRunMixin


class Labgrid(AsyncRunMixin):
    @which(
        "labgrid-client",
        "Use 'pip3 install labgrid-client' to install labgrid software please.",
    )
    def __init__(self):
        pass

    async def labgrid_get_places(self):
        cmd = "labgrid-client p"
        _, places, _ = await self._run_cmd(cmd)
        return places

    async def labgrid_get_reservations(self):
        cmd = "labgrid-client reservations"
        _, reservations_text, _ = await self._run_cmd(cmd)
        try:  # pylint: disable=too-many-nested-blocks
            reservations = yaml.load(reservations_text, Loader=yaml.FullLoader)
        except yaml.YAMLError:
            logging.error(traceback.format_exc())
            return

        return reservations

    async def labgrid_create_reservation(
        self, place, priority=None, wait=False, timeout=None
    ):
        cmd = f"labgrid-client reserve name={place}"
        if timeout:
            cmd = f"timeout {timeout} " + cmd
        if wait:
            cmd += " --wait"
        if priority:
            cmd += f" --prio {priority}"
        await self._run_cmd(cmd)

    async def labgrid_cancel_reservation(self, reservation, quiet=False):
        cmd = f"labgrid-client cancel-reservation {reservation}"
        if quiet:
            cmd += " > /dev/null 2>&1"
        await self._run_cmd(cmd)

    async def labgrid_acquire_place(self, place):
        cmd = f"labgrid-client -p {place} acquire"
        await self._run_cmd(cmd)

    async def labgrid_release_place(self, place, force=False, quiet=False):
        cmd = f"labgrid-client -p {place} release"
        if force:
            cmd += " -k"
        if quiet:
            cmd += " > /dev/null 2>&1"
        await self._run_cmd(cmd)

    async def labgrid_get_place_token(self, place):
        cmd = f"labgrid-client -p {place} show"
        _, place_info_text, _ = await self._run_cmd(cmd)

        token = ""
        place_info_lines = place_info_text.splitlines()
        for line in place_info_lines:
            if line.find("reservation") >= 0:
                token = line.split(":")[-1].strip()
                break
        return token
