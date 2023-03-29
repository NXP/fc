# -*- coding: utf-8 -*-
#
# Copyright 2023 NXP
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


import pytest

from fc_guarder.guarder import Guarder


class TestGuarder:
    @pytest.mark.parametrize("mode, code", [("good", 0), ("bad", 1)])
    def test_ping(self, mocker, mode, code):
        class Output:
            def __init__(self):
                self.status_code = None
                self.text = None

            def __call__(self, mode):
                if mode == "good":
                    self.status_code = 200
                    self.text = "pong"
                else:
                    self.status_code = 502
                    self.text = "error"
                return self

        mocker.patch(
            "requests.get",
            return_value=Output()(mode),
        )

        ret = Guarder.ping()
        assert ret == code
