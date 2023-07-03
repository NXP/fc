#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2023 NXP
#
# SPDX-License-Identifier: MIT


import os
import sys


def main():
    script = os.path.join(
        os.path.abspath(os.path.dirname(__file__)), "fc_client_docker"
    )
    os.execvp(script, [script] + sys.argv[1:])


if __name__ == "__main__":
    main()
