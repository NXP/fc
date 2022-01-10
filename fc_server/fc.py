#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from fc_common.about import __version__
from core.coordinator import Coordinator


def main():
    product_text = r"""
______                                           _    _____                     _ _             _             
|  ___|                                         | |  /  __ \                   | (_)           | |            
| |_ _ __ __ _ _ __ ___   _____      _____  _ __| | _| /  \/ ___   ___  _ __ __| |_ _ __   __ _| |_ ___  _ __ 
|  _| '__/ _` | '_ ` _ \ / _ \ \ /\ / / _ \| '__| |/ / |    / _ \ / _ \| '__/ _` | | '_ \ / _` | __/ _ \| '__|
| | | | | (_| | | | | | |  __/\ V  V / (_) | |  |   <| \__/\ (_) | (_) | | | (_| | | | | | (_| | || (_) | |   
\_| |_|  \__,_|_| |_| |_|\___| \_/\_/ \___/|_|  |_|\_\\____/\___/ \___/|_|  \__,_|_|_| |_|\__,_|\__\___/|_|   
    """
    logging.info(product_text)
    logging.info("VERSION: %s", __version__)

    Coordinator().start()


if __name__ == "__main__":
    main()
