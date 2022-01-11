# -*- coding: utf-8 -*-

import pathlib
import pkg_resources


def get_package_version():
    root = pathlib.Path(__file__) / ".."
    root = root.resolve()

    return (root / "VERSION").read_text(encoding="utf-8").rstrip()


def get_runtime_version(pkg):
    """
    `fc_common` including `VERSION` maybe upgraded by other caller packages,
    so internal package version is the most reliable item,
    fallback to `VERSION` only when in docker release
    """

    try:
        version = pkg_resources.get_distribution(pkg).version
    except Exception:  # pylint: disable=broad-except
        version = get_package_version()

    return version
