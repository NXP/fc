#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import os
import signal
import subprocess
import sys

from getpass import getuser
from socket import gethostname

import prettytable
import requests
import yaml

from fc_common.version import get_runtime_version


class Client:
    @staticmethod
    def status(args):
        specified_resource = args.resource

        fc_server = os.environ.get("FC_SERVER", "http://127.0.0.1:8600")
        output = requests.get(f"{fc_server}/resource")
        output_data = json.loads(output.text)

        ret = output_data.get("rc", -1)
        if ret == 0:
            data = output_data.get("body", {})

            table = prettytable.PrettyTable()
            table.field_names = ["Resource", "Owner", "Comment"]
            for resource in data:
                if len(resource) == 2:
                    resource.append("")
                if specified_resource:
                    if resource[0] == specified_resource:
                        table.add_row(resource)
                        break
                else:
                    table.add_row(resource)
            print(table)
        else:
            print(f"Errorcode {ret} returned from fc coordinator.")
            sys.exit(1)

    @staticmethod
    def lock(args):
        resource = args.resource
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
    def unlock(args):
        me = "/".join(  # pylint: disable=invalid-name
            (
                os.environ.get("LG_HOSTNAME", gethostname()),
                os.environ.get("LG_USERNAME", getuser()),
            )
        )

        resource = args.resource
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
    print(f"FC-CLIENT VERSION: {get_runtime_version('fc-client')}")

    parser = argparse.ArgumentParser()
    parser.set_defaults(func=lambda args: parser.print_help())
    parser.add_argument("-r", "--resource", type=str, help="resource name")

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
        "lock", aliases=("l",), help="labgrid lock resource"
    )
    subparser.set_defaults(func=Client.lock)

    subparser = subparsers.add_parser(
        "unlock", aliases=("u",), help="labgrid unlock resource"
    )
    subparser.set_defaults(func=Client.unlock)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
