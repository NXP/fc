#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2021-2023 NXP
#
# SPDX-License-Identifier: MIT


import argparse
import asyncio
import json
import os
import signal
import socket
import subprocess
import sys
import time
from contextlib import suppress
from getpass import getuser
from socket import gethostname

import aiohttp
import prettytable
import requests
import yaml

from fc_common import which
from fc_common.config import Config
from fc_common.version import get_runtime_version


class Client:
    @staticmethod
    def mode_check():
        fc_server = os.environ.get("FC_SERVER", None)
        lg_crossbar = os.environ.get("LG_CROSSBAR", None)

        if fc_server and lg_crossbar:
            print("MODE: single")
            Client.mode = "single"
        elif fc_server:
            print("MODE: cluster (LG_CROSSBAR not set, fallback to cluster mode)")
            Client.mode = "cluster"
        elif lg_crossbar:
            print("MODE: cluster (FC_SERVER not set, fallback to cluster mode)")
            Client.mode = "cluster"
        else:
            print("MODE: cluster")
            Client.mode = "cluster"

    @staticmethod
    def labgrid_call(args, extras):
        metadata = Client.fetch_metadata(args.resource)
        os.environ["LG_CROSSBAR"] = metadata["lg"]

        os.execvp("labgrid-client", ["labgrid-client", "-p", args.resource] + extras)

    @staticmethod
    def fetch_metadata(filters):
        # single mode
        if Client.mode == "single":
            fc_server = os.environ.get("FC_SERVER", None)
            lg_crossbar = os.environ.get("LG_CROSSBAR", None)

            if filters == "all":
                return {"default": {"fc": fc_server, "lg": lg_crossbar}}
            return {"fc": fc_server, "lg": lg_crossbar}

        # cluster mode
        def check_etcd_cfg():
            etcd_url = Config.load_cfg().get("etcd")
            if not etcd_url:
                print("Fatal: please init cluster settings for your client first")
                sys.exit(1)

        check_etcd_cfg()

        server_address = "/tmp/fc/fc_client_daemon.sock"
        if not os.path.exists("/tmp/fc/fc_client_daemon.pid"):
            with suppress(FileNotFoundError):
                os.remove(server_address)
            client_daemon = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "..",
                "fc_client_daemon",
                "client_daemon.py",
            )
            subprocess.run(["python3", client_daemon], check=True)

        retries = 0
        max_retries = 100
        while not os.path.exists(server_address):
            if retries == max_retries:
                print("Fatal: fc_client_daemon not available")
                sys.exit(1)
            time.sleep(0.1)
            retries += 1

        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            sock.connect(server_address)
        except socket.error as msg:
            print(msg)
            sys.exit(1)

        # {"require": "all"} or {"require": "imx8mm-evk-sh99"}
        msg = {"require": filters}
        json_msg = json.dumps(msg)

        sock.send(json_msg.encode("utf-8"))
        data = sock.recv(1024)
        sock.close()
        return json.loads(data.decode("utf-8"))

    @staticmethod
    def init(extras):
        if extras[0] not in ["etcd"]:
            print("Candidated init para: etcd")
            sys.exit(1)

        if len(extras) == 1:
            print(f"remove {extras[0]}")
            cfg = Config.load_cfg()
            cfg.pop(extras[0], "")
            Config.save_cfg(cfg)
        elif len(extras) == 2:
            print("set")
            cfg = Config.load_cfg()
            cfg.update({extras[0]: extras[1]})
            Config.save_cfg(cfg)
        else:
            print("wrong")

    @staticmethod
    def cluster_info(args):
        if args.resource:
            metadata = Client.fetch_metadata(args.resource)
            print(f"export FC_SERVER={metadata['fc']}")
            print(f"export LG_CROSSBAR={metadata['lg']}")
        else:
            metadata = Client.fetch_metadata("all")

            print(f"Totally {len(metadata)} instances as follows:")
            for instance_name, data in metadata.items():
                print(f"{instance_name}:")
                print(f"  - FC_SERVER: {data['fc']}")
                print(f"  - LG_CROSSBAR: {data['lg']}")

    @staticmethod
    def booking(_):
        async def get_booking(fc_server):
            url = f"{fc_server}/booking"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    output = await response.text()

            return output

        metadata = Client.fetch_metadata("all")

        tasks = [
            get_booking(instance_meta["fc"]) for instance_meta in metadata.values()
        ]
        loop = asyncio.get_event_loop()
        booking_data = loop.run_until_complete(asyncio.gather(*tasks))
        format_booking_data = []
        for index, data in enumerate(booking_data):
            if index == 0:
                format_booking_data.append(data)
            else:
                data_seg = data.split("\n", 1)
                if len(data_seg) > 1:
                    format_booking_data.append(data_seg[1])

        booking = "\n".join(format_booking_data)
        print(booking)

    @staticmethod
    def status(args):
        async def get_status(fc_server):
            specified_resource = args.resource
            specified_farm_type = args.farm_type
            specified_device_type = args.device_type

            if specified_resource:
                url = f"{fc_server}/resource/{specified_resource}"
            elif specified_farm_type and specified_device_type:
                url = (
                    f"{fc_server}/resource"
                    f"?farmtype={specified_farm_type}&devicetype={specified_device_type}"
                )
            elif specified_farm_type:
                url = f"{fc_server}/resource?farmtype={specified_farm_type}"
            elif specified_device_type:
                url = f"{fc_server}/resource?devicetype={specified_device_type}"
            else:
                url = f"{fc_server}/resource"

            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    output = await response.text()

            return json.loads(output)

        metadata = Client.fetch_metadata("all")

        tasks = [get_status(instance_meta["fc"]) for instance_meta in metadata.values()]
        loop = asyncio.get_event_loop()
        resource_data = loop.run_until_complete(asyncio.gather(*tasks))
        resources = sum(resource_data, [])

        table = prettytable.PrettyTable()
        table_width = 4
        for resource in resources:
            table.add_row(resource)
            table_width = len(resource)

        if table_width == 5:
            table.field_names = ["Resource", "Farm", "Status", "Comment", "Info"]
        else:
            table.field_names = ["Resource", "Farm", "Status", "Comment"]

        print(table.get_string(sortby="Resource"))

    @staticmethod
    @which(
        "labgrid-client",
        "Use 'pip3 install labgrid-client' to install labgrid software please.",
    )
    def lock(args):
        resource = args.resource
        metadata = Client.fetch_metadata(resource)

        fc_server = metadata.get("fc", None)
        if not fc_server:
            print("Fatal: invalid resource")
            sys.exit(1)
        else:
            url = f"{fc_server}/resource/{resource}"
            output = requests.get(url)
            output_data = json.loads(output.text)
            if output_data[0][3] != "":
                print("Fatal: non-debuggable resource")
                sys.exit(1)

        os.environ["LG_CROSSBAR"] = metadata["lg"]

        if resource:
            print(f"Try to acquire resource {resource}...")
            with subprocess.Popen(
                ["labgrid-client", "reserve", "--wait", f"name={resource}"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            ) as process:
                try:
                    process.communicate()
                    subprocess.call(["labgrid-client", "-p", resource, "lock"])
                except KeyboardInterrupt:
                    signal.signal(signal.SIGINT, lambda _: "")
                    token = ""
                    for line in process.stdout.readlines():
                        line = line.decode("UTF-8").strip()
                        if line.startswith("token:"):
                            token = line[7:]
                            break
                    if token:
                        subprocess.call(["labgrid-client", "cancel-reservation", token])
                        subprocess.call(
                            ["labgrid-client", "-p", resource, "unlock"],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.STDOUT,
                        )
        else:
            print("No resource specified.")
            sys.exit(1)

    @staticmethod
    @which(
        "labgrid-client",
        "Use 'pip3 install labgrid-client' to install labgrid software please.",
    )
    def unlock(args):
        resource = args.resource
        metadata = Client.fetch_metadata(resource)
        os.environ["LG_CROSSBAR"] = metadata["lg"]

        me = "/".join(  # pylint: disable=invalid-name
            (
                os.environ.get("LG_HOSTNAME", gethostname()),
                os.environ.get("LG_USERNAME", getuser()),
            )
        )

        if resource:  # pylint: disable=too-many-nested-blocks
            cmd = f"labgrid-client -p {resource} show"
            ret, place_info_text = subprocess.getstatusoutput(cmd)
            if ret == 0:
                token = ""
                place_info_lines = place_info_text.splitlines()
                for line in place_info_lines:
                    if line.find("reservation") >= 0:
                        token = line.split(":")[-1].strip()
                        break

                if token:
                    cmd = "labgrid-client reservations"
                    reservations_text = subprocess.check_output(cmd, shell=True)
                    reservations = yaml.load(reservations_text, Loader=yaml.FullLoader)
                    for k, v in reservations.items():  # pylint: disable=invalid-name
                        if k == f"Reservation '{token}'":
                            owner = v["owner"]
                            if owner == me:
                                print("Start to free the place.")
                                signal.signal(signal.SIGINT, lambda _: "")
                                subprocess.call(
                                    ["labgrid-client", "cancel-reservation", token]
                                )
                                subprocess.call(
                                    ["labgrid-client", "-p", resource, "unlock"]
                                )
                            else:
                                print("Fatal: the resource not owned by you.")
                                sys.exit(1)
                            break
            else:
                print(f"Fatal: {place_info_text}")
                sys.exit(1)
        else:
            print("No resource specified.")
            sys.exit(1)


def main():
    print(
        f"FC-CLIENT VERSION: {get_runtime_version('fc-client')}, "
        "HOMEPAGE: https://fc.readthedocs.org/"
    )

    Client.mode_check()

    parser = argparse.ArgumentParser()
    parser.set_defaults(func=lambda args: parser.print_help())
    parser.add_argument(
        "-r", "--resource", "-p", "--place", type=str, help="resource name"
    )
    parser.add_argument("-f", "--farm-type", type=str, help="farm type")
    parser.add_argument("-d", "--device-type", type=str, help="device type")

    args, extras = parser.parse_known_args()

    if (
        len(extras) > 0
        and extras[0]
        in [
            "status",
            "s",
            "lock",
            "l",
            "unlock",
            "u",
            "booking",
            "b",
            "cluster-info",
            "c",
            "init",
            "i",
        ]
        or not args.resource
    ):
        subparsers = parser.add_subparsers(
            dest="command",
            title="available subcommands",
            metavar="COMMAND",
        )

        subparser = subparsers.add_parser(
            "status", aliases=("s",), help="list status of fc resource"
        )
        subparser.set_defaults(func=Client.status)

        subparser = subparsers.add_parser(
            "lock", aliases=("l", "acquire"), help="labgrid lock resource"
        )
        subparser.set_defaults(func=Client.lock)

        subparser = subparsers.add_parser(
            "unlock", aliases=("u", "release"), help="labgrid unlock resource"
        )
        subparser.set_defaults(func=Client.unlock)

        subparser = subparsers.add_parser(
            "booking", aliases=("b",), help="list current booking"
        )
        subparser.set_defaults(func=Client.booking)

        subparser = subparsers.add_parser(
            "cluster-info", aliases=("c",), help="list cluster info"
        )
        subparser.set_defaults(func=Client.cluster_info)

        subparser = subparsers.add_parser("init", aliases=("i",), help="init fc-client")
        subparser.set_defaults(func=Client.init)

        if len(extras) > 0 and extras[0] in ["init", "i"]:
            args, extras = parser.parse_known_args(extras, namespace=args)
            args.func(extras)
        else:
            args = parser.parse_args(extras, namespace=args)
            args.func(args)
    else:
        Client.labgrid_call(args, extras)


if __name__ == "__main__":
    main()
