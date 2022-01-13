#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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
    "version": get_package_version(),
    "author": "Larry Shen",
    "author_email": "larry.shen@nxp.com",
    "license": "MIT",
    "python_requires": ">=3.6",
    "classifiers": [
        "Development Status :: 2 - Pre-Alpha",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3 :: Only",
    ],
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
