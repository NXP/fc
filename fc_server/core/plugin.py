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

from abc import ABC, abstractmethod


class FCPlugin(ABC):
    """
    Base plugin of FC
    Detail framework plugins should realize next interfaces
    `init`, `schedule`, `force_kick_off`
    """

    def __init__(self):
        super().__init__()
        self.schedule_tick = 0
        self.schedule_interval = 1

    @abstractmethod
    async def init(self, driver):
        pass

    @abstractmethod
    async def schedule(self, driver):
        pass

    @abstractmethod
    async def force_kick_off(self, resource):
        pass
