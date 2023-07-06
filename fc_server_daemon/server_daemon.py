# -*- coding: utf-8 -*-
#
# Copyright 2023 NXP
#
# SPDX-License-Identifier: MIT


import logging
import multiprocessing
import os
import signal
import time

import prctl

from fc_common.etcd import Etcd
from fc_common.logger import Logger


class ServerDaemon:
    def __init__(self, daemon_paras):
        self.daemon_paras = daemon_paras
        self.server_daemon = None
        self.logger = logging.getLogger("fc_server_daemon")

    def __action(self):
        prctl.set_pdeathsig(signal.SIGHUP)  # pylint: disable=no-member

        Logger.init("fc_server_daemon", "fc_server_daemon.log", log_type="file_only")

        self.logger.info("Start fc-server-daemon")
        self.logger.info(self.daemon_paras)

        etcd = Etcd(self.daemon_paras["etcd"])

        # pylint: disable=protected-access
        self.logger.info("Current endpoint: %s", etcd()._current_endpoint_label)

        etcd.put(
            f"/instances/{self.daemon_paras['instance_name']}/fc",
            self.daemon_paras["fc"],
        )
        etcd.put(
            f"/instances/{self.daemon_paras['instance_name']}/lg",
            self.daemon_paras["lg"],
        )
        for device in self.daemon_paras["devices"]:
            etcd.put(f"/devices/{device}", self.daemon_paras["instance_name"])

        ttl = 60
        while True:
            try:
                self.logger.info("  - try to lock instance")
                with etcd().lock(
                    f"instances/{self.daemon_paras['instance_name']}", ttl
                ) as lock:
                    self.logger.info("  - instance locked successfully")
                    while True:
                        time.sleep(ttl / 4)
                        lock.refresh()
            except Exception as lock_exec:  # pylint: disable=broad-except
                self.logger.debug(lock_exec)

            time.sleep(30)

    def handler(self, *_):
        if self.server_daemon:
            os.kill(self.server_daemon.pid, signal.SIGINT)

    def run(self):
        self.server_daemon = multiprocessing.Process(target=self.__action, daemon=True)
        self.server_daemon.start()

        signal.signal(signal.SIGTERM, self.handler)
