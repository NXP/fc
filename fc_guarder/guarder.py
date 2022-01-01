#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import os
import sys
import time
import requests

management_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "management")
)
sys.path.append(management_path)

# pylint: disable=wrong-import-position
from cmd_online_lava_devices import LavaManagement
from about import __version__


class Guarder:
    @staticmethod
    def ping():
        fc_server = os.environ.get("FC_SERVER", "http://127.0.0.1:8600")

        output = None
        try:
            output = requests.get(f"{fc_server}/ping")
            if output.status_code == 200 and output.text == "pong":
                return 0
        except Exception as exception:  # pylint: disable=broad-except
            print(exception)

        return 1

    @staticmethod
    def restore_lava():
        asyncio.run(LavaManagement().action())


def main():
    print("FC guarder start.")
    print(f"VERSION: {__version__}")

    default_interval = int(os.environ.get("FC_GUARDER_DEFAULT_INTERVAL", "600"))
    min_interval = int(os.environ.get("FC_GUARDER_MIN_INTERVAL", "60"))
    max_interval = int(os.environ.get("FC_GUARDER_MAX_INTERVAL", "1800"))
    max_cordon = int(os.environ.get("FC_GUARDER_MAX_CORDON", "10"))

    asleep = False
    cordon = 0
    interval = default_interval

    while True:
        ret = Guarder.ping()
        if ret == 0:
            asleep = False
            cordon = 0
            interval = default_interval
        else:
            if not asleep:
                cordon += 1
                interval = min_interval
                if cordon > max_cordon:
                    asleep = True
                    cordon = 0
                    interval = max_interval

                    # restore lava
                    print("Restore lava now.")
                    Guarder.restore_lava()
                    print("Restore lava done.")
        time.sleep(interval)


if __name__ == "__main__":
    main()
