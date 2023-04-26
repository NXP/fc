# -*- coding: utf-8 -*-
#
# Copyright 2023 NXP
#
# SPDX-License-Identifier: MIT


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
