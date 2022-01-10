# -*- coding: utf-8 -*-

import asyncio


class AsyncRunMixin:  # pylint: disable=too-few-public-methods
    """
    Mixin for async subprocess call
    """

    async def _run_cmd(self, cmd):  # pylint: disable=no-self-use
        proc = await asyncio.create_subprocess_shell(
            cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            print(f"[{cmd!r} exited with {proc.returncode}]")
        if stderr:
            print(f"[{cmd!r} stderr]\n{stderr.decode()}")

        return proc.returncode, stdout, stderr


class FCPlugin:
    """
    Base plugin of FC
    Detail framework plugins should realize `init`, `schedule` interfaces
    """

    def __init__(self):
        self.schedule_tick = 0
        self.schedule_interval = 1

    async def init(self, driver):
        raise NotImplementedError(f"Define in the subclass: {self}")

    async def schedule(self, driver):
        raise NotImplementedError(f"Define in the subclass: {self}")

    async def force_kick_off(self, resource):
        raise NotImplementedError(f"Define in the subclass: {self}")
