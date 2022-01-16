# -*- coding: utf-8 -*-


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
