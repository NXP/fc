# -*- coding: utf-8 -*-
#
# Copyright 2022-2023 NXP
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
        self.logger = logging.getLogger("fc_server")

    async def labgrid_get_places(self):
        cmd = "labgrid-client -v p"
        _, places, _ = await self._run_cmd(cmd)
        place_line = places.splitlines()
        return [line.split("'")[1] for line in place_line if line.find("Place") >= 0]

    async def labgrid_get_comments(self):
        comments = {}
        cmd = "labgrid-client -v p"
        _, places, _ = await self._run_cmd(cmd)
        place_line = places.splitlines()
        try_to_parse_comment = False
        for line in place_line:
            if line.find("Place") >= 0:
                place = line.split("'")[1]
                try_to_parse_comment = True
                continue
            if try_to_parse_comment:
                if line.find("comment: ") > 0:
                    comments[place] = line.split("comment: ")[1]
                try_to_parse_comment = False
        return comments

    async def labgrid_get_reservations(self):
        cmd = "labgrid-client reservations"
        _, reservations_text, _ = await self._run_cmd(cmd)
        try:  # pylint: disable=too-many-nested-blocks
            reservations = yaml.load(reservations_text, Loader=yaml.FullLoader)
        except yaml.YAMLError:
            self.logger.error(traceback.format_exc())
            return

        return reservations

    async def labgrid_create_reservation(
        self, place, priority=None, wait=False, shell=False, timeout=None
    ):
        cmd = f"labgrid-client reserve name={place}"
        if timeout:
            cmd = f"timeout {timeout} " + cmd
        if shell:
            cmd += " --shell"
        if wait:
            cmd += " --wait"
        if priority:
            cmd += f" --prio {priority}"
        ret_cmd = await self._run_cmd(cmd)

        if shell and ret_cmd[0] == 0:
            token_string = ret_cmd[1].split("export LG_TOKEN=")
            reservation = None
            if len(token_string) == 2:
                reservation = token_string[1]
            return ret_cmd, reservation

        return ret_cmd

    async def labgrid_cancel_reservation(self, reservation, quiet=False):
        cmd = f"labgrid-client cancel-reservation {reservation}"
        if quiet:
            cmd += " > /dev/null 2>&1"
        await self._run_cmd(cmd)

    async def labgrid_acquire_place(self, place):
        cmd = f"labgrid-client -p {place} acquire"
        return await self._run_cmd(cmd)

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

    async def labgrid_get_place_owner(self, place):
        cmd = f"labgrid-client -p {place} show"
        _, place_info_text, _ = await self._run_cmd(cmd)

        owner = ""
        place_info_lines = place_info_text.splitlines()
        for line in place_info_lines:
            if line.find("acquired:") >= 0:
                owner = line.split(":")[-1].strip()
                break
        return owner
