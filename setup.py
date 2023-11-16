#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2021-2023 NXP
#
# SPDX-License-Identifier: MIT


import os
import pathlib
import signal
import sys

import pkg_resources
from setuptools import Command, find_packages, setup
from setuptools.command.install import install

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


class InstallCommand(install):
    """Custom install command to clear old client daemon"""

    def run(self):
        super().run()

        pid_file = "/tmp/fc/fc_client_daemon.pid"
        if os.path.exists(pid_file):
            pid_path = pathlib.Path(pid_file)
            pid = int(pid_path.read_text(encoding="utf-8").rstrip())
            try:
                os.kill(pid, signal.SIGINT)
            except:  # pylint: disable=bare-except
                pass


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
        packages=find_packages(include=("fc_common", "fc_server*", "fc_server_daemon")),
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
            "aiohttp>=3.7.4.post0",
            "async-lru>=1.0.3",
            "flatdict>=4.0.1",
            "lavacli==1.2",
            "labgrid==23.0.1",
            "singledispatchmethod>=1.0",
            "python-prctl",
            "etcd3-fc",
            "tenacity",
            "protobuf==3.20.3",
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
    common_setup["cmdclass"].update({"install": InstallCommand})
    setup(
        **common_setup,
        name="fc-client",
        packages=["fc_common", "fc_client", "fc_client_daemon"],
        package_data={
            "fc_common": ["VERSION"],
        },
        entry_points={
            "console_scripts": [
                "fc-client = fc_client.client:main",
            ]
        },
        install_requires=[
            "prettytable>=2.2.1",
            "python-daemon",
            "etcd3-fc",
            "tenacity",
            "aiohttp",
            "psutil",
            "protobuf==3.20.3",
        ],
        extras_require={
            "labgrid": ["labgrid==23.0.1"],
        },
    )
elif PKG == "fc-client-docker":
    setup(
        **common_setup,
        name="fc-client-docker",
        packages=["fc_common", "fc_client_docker"],
        package_data={
            "fc_common": ["VERSION"],
            "fc_client_docker": ["fc_client_docker"],
        },
        entry_points={
            "console_scripts": [
                "fc-client-docker = fc_client_docker:main",
            ]
        },
        python_requires=">=3",
    )
