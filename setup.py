#!/usr/bin/env python3
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


import os
import pathlib
import sys
import pkg_resources

from setuptools import find_packages, setup, Command

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

LABGRID_PYSERIAL_FIX = "pyserial-labgrid==3.4.0.1"

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
            "flatdict==4.0.1",
            "lavacli==1.2",
            "labgrid==0.4.1",
            LABGRID_PYSERIAL_FIX,
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
            "labgrid==0.4.1",
            LABGRID_PYSERIAL_FIX,
        ],
    )
