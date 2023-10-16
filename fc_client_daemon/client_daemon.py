#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2023 NXP
#
# SPDX-License-Identifier: MIT


import json
import logging
import os
import signal
import socket
from threading import Lock

import daemon
from daemon import pidfile

from fc_common.config import Config
from fc_common.etcd import Etcd
from fc_common.logger import Logger


class ClientDaemon:
    # pylint: disable=too-many-instance-attributes
    def __init__(self):
        self.logger = logging.getLogger("fc_client_daemon")

        etcd_url = Config.load_cfg().get("etcd")
        self.logger.info("Etcd url: %s", etcd_url)
        self.etcd = Etcd(etcd_url)
        self.logger.info("Current endpoint: %s", self.etcd()._current_endpoint_label)

        self.locks_prefix = "/locks/instances/"
        self.locks_prefix_len = len(self.locks_prefix)

        self.devices_prefix = "/devices/"
        self.devices_prefix_len = len(self.devices_prefix)

        self.instance_data = {}
        self.device_data = {}

        self.lock = Lock()

        self.ipc_server_address = "\0/tmp/fc/fc_client_daemon.sock"

    def watch_locks_callback(self, event):
        try:
            for per_event in event.events:
                if isinstance(per_event, Etcd.DeleteEvent):
                    self.logger.info("Delete event:")
                    self.logger.info(per_event.key)

                    instance_name = per_event.key[self.locks_prefix_len :].decode(
                        "utf-8"
                    )
                    with self.lock:
                        self.instance_data.pop(instance_name)

                elif isinstance(per_event, Etcd.PutEvent):
                    self.logger.info("Put event:")
                    self.logger.info(per_event.key)

                    instance_name = per_event.key[self.locks_prefix_len :].decode(
                        "utf-8"
                    )
                    fc_addr = self.etcd.get("/instances/" + instance_name + "/fc")[
                        0
                    ].decode("utf-8")
                    lg_addr = self.etcd.get("/instances/" + instance_name + "/lg")[
                        0
                    ].decode("utf-8")

                    self.logger.info(fc_addr)
                    self.logger.info(lg_addr)

                    with self.lock:
                        self.instance_data.setdefault(instance_name, {})
                        self.instance_data[instance_name]["fc"] = fc_addr
                        self.instance_data[instance_name]["lg"] = lg_addr
        except Exception as locks_cb_exec:  # pylint: disable=broad-except
            self.logger.info(locks_cb_exec)
            # Exit due to issue of https://github.com/kragniz/python-etcd3/issues/1026
            os.kill(os.getpid(), signal.SIGINT)

    def watch_devices_callback(self, event):
        try:
            for per_event in event.events:
                if isinstance(per_event, Etcd.PutEvent):
                    self.logger.info("put device event")

                    device_value = per_event.value.decode("utf-8")
                    device_name = per_event.key[self.devices_prefix_len :].decode(
                        "utf-8"
                    )

                    self.logger.info(device_name)
                    self.logger.info(device_value)

                    with self.lock:
                        self.device_data[device_name] = device_value
        except Exception as devices_cb_exec:  # pylint: disable=broad-except
            self.logger.info(devices_cb_exec)
            # Exit due to issue of https://github.com/kragniz/python-etcd3/issues/1026
            os.kill(os.getpid(), signal.SIGINT)

    def start_data_channel(self):
        self.logger.info("Start data channel.")

        instances = self.etcd.get_prefix(self.locks_prefix)
        for instance in instances:
            instance_name = instance[1].key[self.locks_prefix_len :].decode("utf-8")
            fc_addr = self.etcd.get("/instances/" + instance_name + "/fc")[0].decode(
                "utf-8"
            )
            lg_addr = self.etcd.get("/instances/" + instance_name + "/lg")[0].decode(
                "utf-8"
            )
            self.logger.info(instance)
            self.logger.info(fc_addr)
            self.logger.info(lg_addr)

            self.instance_data.setdefault(instance_name, {})
            self.instance_data[instance_name]["fc"] = fc_addr
            self.instance_data[instance_name]["lg"] = lg_addr

        devices = self.etcd.get_prefix(self.devices_prefix)
        for device in devices:
            self.device_data[
                device[1].key[self.devices_prefix_len :].decode("utf-8")
            ] = device[0].decode("utf-8")

        self.etcd.add_watch_prefix_callback(
            self.locks_prefix, self.watch_locks_callback
        )
        self.etcd.add_watch_prefix_callback(
            self.devices_prefix, self.watch_devices_callback
        )

    def start_ipc_server(self):
        self.logger.info("Start ipc server.")

        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(self.ipc_server_address)
        server.listen()

        while True:
            client_socket, _ = server.accept()
            data = client_socket.recv(1024)

            self.logger.info(data)

            msg = json.loads(data.decode("utf-8"))
            with self.lock:
                if msg["msg_type"] == "require_info":
                    if msg["para"] == "all":
                        self.logger.info(self.instance_data)
                        client_socket.send(
                            json.dumps(self.instance_data).encode("utf-8")
                        )
                    else:
                        try:
                            logger.info(self.device_data[msg["para"]])
                            return_data = self.instance_data[
                                self.device_data[msg["para"]]
                            ]
                        except Exception as ipc_exec:  # pylint: disable=broad-except
                            return_data = {}
                            self.logger.info(ipc_exec)
                        client_socket.send(json.dumps(return_data).encode("utf-8"))
                elif msg["msg_type"] == "daemon_stop":
                    client_socket.send("ok")
                    os.kill(os.getpid(), signal.SIGINT)


if __name__ == "__main__":
    TMP_FC_PATH = "/tmp/fc"
    if not os.path.exists(TMP_FC_PATH):
        os.makedirs(TMP_FC_PATH)
        os.chmod(TMP_FC_PATH, 0o777)

    os.environ["FC_LOG_PATH"] = TMP_FC_PATH
    Logger.init(
        "fc_client_daemon",
        "fc_client_daemon.log",
        log_type="file_only",
        log_file_permission=0o777,
    )

    logger = logging.getLogger("fc_client_daemon")
    logger.info("Start fc-client-daemon")

    logger_io = [handler.stream for handler in logger.handlers]
    with daemon.DaemonContext(
        umask=0o002,
        pidfile=pidfile.TimeoutPIDLockFile("/tmp/fc/fc_client_daemon.pid"),
        files_preserve=logger_io,
    ) as context:
        try:
            client_daemon = ClientDaemon()
            client_daemon.start_data_channel()
            client_daemon.start_ipc_server()
        except Exception as daemon_exec:  # pylint: disable=broad-except
            logger.info(daemon_exec)
