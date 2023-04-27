#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2021-2023 NXP
#
# SPDX-License-Identifier: MIT


import os
import pathlib
import sys

import pkg_resources
from setuptools import Command, find_packages, setup

from fc_common.version import get_package_version


class CleanCommand(Command):
    """Custom clean command to tidy up the project root."""

    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):  # pylint: disable=no-self-use
        os.system("rm -vrf ./build ./dist ./*.pyc ./*.tgz ./*.egg-info ./__pycache__")


def get_project_name():
    for dist in pkg_resources.AvailableDistributions():
        if dist.startswith("fc"):
            try:
                pathlib.Path(__file__).relative_to(
                    pkg_resources.get_distribution(dist).location
                )
            except ValueError:
                pass
            else:
                return dist
    return "fc-client"


if sys.argv[-1].startswith("fc"):
    PKG = sys.argv.pop()
else:
    PKG = get_project_name()

common_setup = {
    "cmdclass": {
        "clean": CleanCommand,
    },
}

if PKG == "fc-server":
    setup(
        **common_setup,
        name="fc-server",
        packages=find_packages(include=("fc_common", "fc_server*")),
        package_data={
            "fc_common": ["VERSION"],
            "fc_server": ["config/sample_cfg.yaml", "config/sample_lavacli.yaml"],
        },
        entry_points={
            "console_scripts": [
                "fc-server = fc_server.server:main",
            ]
        },
        install_requires=[
            "aiohttp==3.7.4.post0",
            "async-lru==1.0.3",
            "flatdict==4.0.1",
            "lavacli==1.2",
            "labgrid==23.0.1",
            "singledispatchmethod==1.0",
        ],
    )
elif PKG == "fc-guarder":
    setup(
        **common_setup,
        name="fc-guarder",
        packages=["fc_guarder"],
        entry_points={
            "console_scripts": [
                "fc-guarder = fc_guarder.guarder:main",
            ]
        },
        install_requires=[f"fc-server=={get_package_version()}"],
    )
elif PKG == "fc-client":
    setup(
        **common_setup,
        name="fc-client",
        packages=["fc_common", "fc_client"],
        package_data={
            "fc_common": ["VERSION"],
        },
        entry_points={
            "console_scripts": [
                "fc-client = fc_client.client:main",
            ]
        },
        install_requires=[
            "prettytable==2.2.1",
            "labgrid==23.0.1",
        ],
    )
