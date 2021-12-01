# -*- coding: utf-8 -*-
# vim: set ts=4

# Copyright 2017 Rémi Duraffort
# This file is part of lavacli.
#
# lavacli is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# lavacli is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with lavacli.  If not, see <http://www.gnu.org/licenses/>

import argparse
import contextlib
import datetime
import json
import pathlib
import sys
import time
from urllib.parse import urlparse
import xmlrpc.client
import yaml

from lavacli.utils import loader, print_u, exc2str


def configure_log_options(parser):
    parser.add_argument(
        "--filters",
        default=None,
        type=str,
        help="comma seperated list of levels to show",
    )
    parser.add_argument(
        "--polling",
        default=5,
        type=int,
        help="polling interval in seconds [default=5s]",
    )
    parser.add_argument(
        "--raw", default=False, action="store_true", help="print raw logs"
    )
    parser.add_argument("--start", default=0, type=int, help="start at the given line")
    parser.add_argument("--end", default=None, type=int, help="end at the given line")


def configure_parser(parser, version):
    sub = parser.add_subparsers(dest="sub_sub_command", help="Sub commands")
    sub.required = True

    # "cancel"
    jobs_cancel = sub.add_parser("cancel", help="cancel a job")
    jobs_cancel.add_argument("job_id", nargs="+", help="job id")

    if version >= (2018, 4):
        # "config"
        jobs_config = sub.add_parser("config", help="job configuration")
        jobs_config.add_argument("job_id", help="job id")
        jobs_config.add_argument(
            "--dest", default=".", help="save files into this directory"
        )

    # "definition"
    jobs_definition = sub.add_parser("definition", help="job definition")
    jobs_definition.add_argument("job_id", help="job id")

    # "list"
    jobs_list = sub.add_parser("list", help="list jobs")
    if version >= (2018, 4):
        jobs_list.add_argument(
            "--state",
            type=str,
            default=None,
            choices=[
                "SUBMITTED",
                "SCHEDULING",
                "SCHEDULED",
                "RUNNING",
                "CANCELING",
                "FINISHED",
            ],
            help="filter jobs by state",
        )
        jobs_list.add_argument(
            "--health",
            type=str,
            default=None,
            choices=["UNKNOWN", "COMPLETE", "INCOMPLETE", "CANCELED"],
            help="filter jobs by health",
        )
    if version >= (2018, 10):
        jobs_list.add_argument(
            "--since",
            type=int,
            default=0,
            help="Filter by jobs which completed in the last N minutes.",
        )
        jobs_list.add_argument(
            "--verbose",
            dest="verbose",
            action="store_true",
            help="If verbose is True, add extra keys, including error_type.",
        )
    jobs_list.add_argument(
        "--start", type=int, default=0, help="skip the N first jobs [default=0]"
    )
    jobs_list.add_argument(
        "--limit", type=int, default=25, help="limit to N jobs [default=25]"
    )
    out_format = jobs_list.add_mutually_exclusive_group()
    out_format.add_argument(
        "--json",
        dest="output_format",
        default=None,
        action="store_const",
        const="json",
        help="print as json",
    )
    out_format.add_argument(
        "--yaml",
        dest="output_format",
        default=None,
        action="store_const",
        const="yaml",
        help="print as yaml",
    )

    # "logs"
    jobs_logs = sub.add_parser("logs", help="get logs")
    jobs_logs.add_argument("job_id", help="job id")
    jobs_logs.add_argument(
        "--no-follow",
        default=False,
        action="store_true",
        help="do not keep polling until the end of the job",
    )
    configure_log_options(jobs_logs)

    # "queue"
    if version >= (2019, 1):
        jobs_queue = sub.add_parser("queue", help="job queue")
        jobs_queue.add_argument(
            "device_types", nargs="*", help="filter by device-types"
        )
        out_format = jobs_queue.add_mutually_exclusive_group()
        out_format.add_argument(
            "--json",
            dest="output_format",
            default=None,
            action="store_const",
            const="json",
            help="print as json",
        )
        out_format.add_argument(
            "--yaml",
            dest="output_format",
            action="store_const",
            const="yaml",
            default=None,
            help="print as yaml",
        )
        jobs_queue.add_argument(
            "--start", type=int, default=0, help="skip the N first jobs [default=0]"
        )
        jobs_queue.add_argument(
            "--limit", type=int, default=25, help="limit to N jobs [default=25]"
        )

    # "resubmit"
    jobs_resubmit = sub.add_parser("resubmit", help="resubmit a job")
    jobs_resubmit.add_argument("job_id", help="job id")
    jobs_resubmit.add_argument(
        "--url",
        action="store_true",
        dest="print_url",
        default=False,
        help="Print the full url",
    )
    jobs_resubmit.add_argument(
        "--follow",
        default=True,
        dest="no_follow",
        action="store_false",
        help="resubmit and poll for the logs",
    )
    configure_log_options(jobs_resubmit)

    # "run"
    jobs_run = sub.add_parser("run", help="run the job")
    jobs_run.add_argument(
        "definition", type=argparse.FileType("r"), help="job definition"
    )
    jobs_run.add_argument(
        "--filters",
        default=None,
        type=str,
        help="comma seperated list of levels to show",
    )
    jobs_run.add_argument(
        "--no-follow",
        default=False,
        action="store_true",
        help="do not keep polling until the end of the job",
    )
    jobs_run.add_argument(
        "--polling",
        default=5,
        type=int,
        help="polling interval in seconds [default=5s]",
    )
    jobs_run.add_argument(
        "--raw", default=False, action="store_true", help="print raw logs"
    )
    jobs_run.add_argument(
        "--start", default=0, type=int, help="start at the given line"
    )
    jobs_run.add_argument("--end", default=None, type=int, help="end at the given line")

    # "show"
    jobs_show = sub.add_parser("show", help="job details")
    jobs_show.add_argument("job_id", help="job id")
    out_format = jobs_show.add_mutually_exclusive_group()
    out_format.add_argument(
        "--json",
        dest="output_format",
        default=None,
        action="store_const",
        const="json",
        help="print as json",
    )
    out_format.add_argument(
        "--yaml",
        dest="output_format",
        action="store_const",
        const="yaml",
        default=None,
        help="print as yaml",
    )

    # "submit"
    jobs_submit = sub.add_parser("submit", help="submit a new job")
    jobs_submit.add_argument(
        "definition", nargs="+", type=argparse.FileType("r"), help="job definition"
    )
    jobs_submit.add_argument(
        "--url",
        action="store_true",
        dest="print_url",
        default=False,
        help="Print the full url",
    )
    jobs_submit.add_argument(
        "--follow",
        default=True,
        dest="no_follow",
        action="store_false",
        help="resubmit and poll for the logs",
    )
    configure_log_options(jobs_submit)

    if version >= (2019, 3):
        # "validate"
        jobs_validate = sub.add_parser("validate", help="validate the job definition")
        jobs_validate.add_argument(
            "definition", type=argparse.FileType("r"), help="job definition"
        )
        jobs_validate.add_argument(
            "--strict", action="store_true", default=False, help="check in strict mode"
        )

    if version >= (2018, 1):
        # "wait"
        jobs_wait = sub.add_parser("wait", help="wait for the job to finish")
        jobs_wait.add_argument("job_id", help="job id")
        jobs_wait.add_argument(
            "--polling",
            default=5,
            type=int,
            help="polling interval in seconds [default=5s]",
        )
        jobs_wait.add_argument(
            "--timeout",
            default=0,
            type=int,
            help="Maximum time to wait in seconds, 0 to disable [default=0s]",
        )


def help_string():
    return "manage jobs"


def handle_cancel(proxy, options, _):
    for job_id in options.job_id:
        try:
            proxy.scheduler.jobs.cancel(job_id)
        except xmlrpc.client.Error as exc:
            print("Unable to cancel job %s: %s" % (job_id, exc2str(exc)))
    return 0


def handle_config(proxy, options, _):
    config = proxy.scheduler.jobs.configuration(options.job_id)
    definition, device, dispatcher, env, env_dut = config

    # Create the directory if needed
    dest = pathlib.Path(options.dest)
    with contextlib.suppress(FileExistsError):
        dest.mkdir(mode=0o755)

    # Save the files
    with (dest / "definition.yaml").open("w") as f_out:
        f_out.write(definition)
    if device is not None:
        with (dest / "device.yaml").open("w") as f_out:
            f_out.write(device)
    if dispatcher is not None:
        with (dest / "dispatcher.yaml").open("w") as f_out:
            f_out.write(dispatcher)
    if env is not None:
        with (dest / "env.yaml").open("w") as f_out:
            f_out.write(env)
    if env_dut is not None:
        with (dest / "env.dut.yaml").open("w") as f_out:
            f_out.write(env_dut)
    return 0


def handle_definition(proxy, options, _):
    print(proxy.scheduler.jobs.definition(options.job_id))
    return 0


def handle_list(proxy, options, config):
    if config["version"] >= (2018, 10):
        jobs = proxy.scheduler.jobs.list(
            options.state,
            options.health,
            options.start,
            options.limit,
            options.since,
            options.verbose,
        )
    elif config["version"] >= (2018, 4):
        jobs = proxy.scheduler.jobs.list(
            options.state, options.health, options.start, options.limit
        )
    else:
        jobs = proxy.scheduler.jobs.list(options.start, options.limit)

    if options.output_format == "json":
        print(json.dumps(jobs))
    elif options.output_format == "yaml":
        print(yaml.dump(jobs, default_flow_style=None).rstrip("\n"))
    else:
        print(
            "Jobs (from %s to %s):" % (1 + options.start, options.start + options.limit)
        )
        for job in jobs:
            if config["version"] >= (2018, 10) and options.verbose:
                if job["error_type"]:
                    print(
                        "* %s: %s,%s [%s] (%s) - %s %s <%s> <%s> %s: %s"
                        % (
                            job["id"],
                            job["state"],
                            job["health"],
                            job["submitter"],
                            job["description"],
                            job["device_type"],
                            job["actual_device"],
                            job["start_time"],
                            job["end_time"],
                            job["error_type"],
                            job["error_msg"],
                        )
                    )
                else:
                    print(
                        "* %s: %s,%s [%s] (%s) - %s %s <%s> <%s>"
                        % (
                            job["id"],
                            job["state"],
                            job["health"],
                            job["submitter"],
                            job["description"],
                            job["device_type"],
                            job["actual_device"],
                            job["start_time"],
                            job["end_time"],
                        )
                    )

            elif config["version"] >= (2018, 1):
                print(
                    "* %s: %s,%s [%s] (%s) - %s"
                    % (
                        job["id"],
                        job["state"],
                        job["health"],
                        job["submitter"],
                        job["description"],
                        job["device_type"],
                    )
                )
            else:
                print(
                    "* %s: %s [%s] (%s) - %s"
                    % (
                        job["id"],
                        job["status"],
                        job["submitter"],
                        job["description"],
                        job["device_type"],
                    )
                )
    return 0


if sys.stdout.isatty():
    COLORS = {
        "exception": "\033[1;31m",
        "error": "\033[1;31m",
        "warning": "\033[1;33m",
        "info": "\033[1;37m",
        "debug": "\033[0;37m",
        "target": "\033[32m",
        "input": "\033[0;35m",
        "feedback": "\033[0;33m",
        "results": "\033[1;34m",
        "dt": "\033[0;90m",
        "end": "\033[0m",
    }
else:
    COLORS = {
        "exception": "",
        "error": "",
        "warning": "",
        "info": "",
        "debug": "",
        "target": "",
        "input": "",
        "feedback": "",
        "results": "",
        "dt": "",
        "end": "",
    }


def print_logs(logs, raw, filters):
    filters = [] if filters is None else filters.split(",")
    if raw:
        for line in logs:
            if filters and not line["lvl"] in filters:
                continue
            print_u(
                "- "
                + yaml.dump(
                    line,
                    default_flow_style=True,
                    default_style='"',
                    width=10 ** 6,
                    Dumper=yaml.CDumper,
                )[:-1]
            )
    else:
        for line in logs:
            timestamp = line["dt"].split(".")[0]
            level = line["lvl"]
            if filters and level not in filters:
                continue
            if isinstance(line["msg"], dict) and "sending" in line["msg"].keys():
                level = "input"
                msg = str(line["msg"]["sending"])
            elif isinstance(line["msg"], bytes):
                msg = line["msg"].decode("utf-8", errors="replace")
            else:
                msg = str(line["msg"])
            msg = msg.rstrip("\n")

            print_u(
                COLORS["dt"]
                + timestamp
                + COLORS["end"]
                + " "
                + COLORS[level]
                + msg
                + COLORS["end"]
            )


def _download_logs(proxy, version, job_id, start, end):
    if version >= (2018, 6):
        (finished, data) = proxy.scheduler.jobs.logs(job_id, start, end)
        logs = yaml.load(str(data), Loader=loader(False))
    else:
        (finished, data) = proxy.scheduler.jobs.logs(job_id, start)
        logs = yaml.load(str(data), Loader=loader(False))
        if end is not None and len(logs) >= end - start:
            if end < start:
                end = start
            logs = logs[: end - start]
    return (finished, logs)


def handle_logs(proxy, options, config):
    # Loop
    lines = options.start
    while True:
        (finished, logs) = _download_logs(
            proxy, config["version"], options.job_id, lines, options.end
        )
        if logs:
            print_logs(logs, options.raw, options.filters)
            lines += len(logs)
        # Loop only if the job is not finished
        if (
            finished
            or options.no_follow
            or (options.end is not None and lines >= options.end)
        ):
            break

        # Wait some time
        time.sleep(options.polling)

    # Print the failure comment if the job is finished
    if finished:
        details = proxy.scheduler.jobs.show(options.job_id)
        if details.get("failure_comment"):
            print_logs(
                [
                    {
                        "dt": datetime.datetime.utcnow().isoformat(),
                        "lvl": "info",
                        "msg": "[lavacli] Failure comment: %s"
                        % details["failure_comment"],
                    }
                ],
                options.raw,
                options.filters,
            )
    return 0


def handle_queue(proxy, options, config):
    dts = options.device_types if options.device_types else None
    data = proxy.scheduler.jobs.queue(dts, options.start, options.limit)
    if options.output_format == "json":
        print(json.dumps(data))
    elif options.output_format == "yaml":
        print(yaml.dump(data, default_flow_style=None).rstrip("\n"))
    else:
        print(
            "Jobs (from %s to %s):" % (1 + options.start, options.start + options.limit)
        )
        for job in data:
            print(
                "* %s: %s (%s) - %s"
                % (
                    job["id"],
                    job["submitter"],
                    job["description"] if job["description"] else "",
                    job["requested_device_type"],
                )
            )
    return 0


def handle_resubmit(proxy, options, config):
    job_id = proxy.scheduler.jobs.resubmit(options.job_id)

    if options.no_follow:
        prefix = ""
        if options.print_url:
            parsed = urlparse(options.uri)
            host = parsed.netloc.split("@")[-1]
            prefix = "%s://%s/scheduler/job/" % (parsed.scheme, host)

        if isinstance(job_id, list):
            for job in job_id:
                print(prefix + str(job))
        else:
            print(prefix + str(job_id))

    else:
        print_logs(
            [
                {
                    "dt": datetime.datetime.utcnow().isoformat(),
                    "lvl": "info",
                    "msg": "[lavacli] Job %s submitted" % job_id,
                }
            ],
            options.raw,
            options.filters,
        )

        follow_logs(job_id, proxy, options, config)
    return 0


def follow_logs(job_id, proxy, options, config):
    # Add the job_id to options for handle_logs
    # For multinode, print something and loop on all jobs
    if isinstance(job_id, list):
        for job in job_id:
            print_logs(
                [
                    {
                        "dt": datetime.datetime.utcnow().isoformat(),
                        "lvl": "info",
                        "msg": "[lavacli] Seeing %s logs" % job,
                    }
                ],
                options.raw,
                options.filters,
            )
            options.job_id = job
            handle_logs(proxy, options, config)
    else:
        options.job_id = str(job_id)
        handle_logs(proxy, options, config)


def handle_run(proxy, options, config):
    job_id = proxy.scheduler.jobs.submit(options.definition.read())
    print_logs(
        [
            {
                "dt": datetime.datetime.utcnow().isoformat(),
                "lvl": "info",
                "msg": "[lavacli] Job %s submitted" % job_id,
            }
        ],
        options.raw,
        options.filters,
    )

    # Add the job_id to options for handle_logs
    # For multinode, print something and loop on all jobs
    if isinstance(job_id, list):
        for job in job_id:
            print_logs(
                [
                    {
                        "dt": datetime.datetime.utcnow().isoformat(),
                        "lvl": "info",
                        "msg": "[lavacli] Seeing %s logs" % job,
                    }
                ],
                options.raw,
                options.filters,
            )
            options.job_id = job
            handle_logs(proxy, options, config)
    else:
        options.job_id = job_id
        handle_logs(proxy, options, config)
    return 0


def handle_show(proxy, options, config):
    job = proxy.scheduler.jobs.show(options.job_id)

    if options.output_format == "json":
        job["submit_time"] = job["submit_time"].value if job["submit_time"] else None
        job["start_time"] = job["start_time"].value if job["start_time"] else None
        job["end_time"] = job["end_time"].value if job["end_time"] else None
        print(json.dumps(job))
    elif options.output_format == "yaml":
        job["submit_time"] = job["submit_time"].value if job["submit_time"] else None
        job["start_time"] = job["start_time"].value if job["start_time"] else None
        job["end_time"] = job["end_time"].value if job["end_time"] else None
        print(yaml.dump(job, default_flow_style=None).rstrip("\n"))
    else:
        print("id          : %s" % job["id"])
        print("description : %s" % job["description"])
        print("submitter   : %s" % job["submitter"])
        print("device-type : %s" % job["device_type"])
        print("device      : %s" % job["device"])
        print("health-check: %s" % job["health_check"])
        if config["version"] >= (2018, 1):
            print("state       : %s" % job["state"])
            print("Health      : %s" % job["health"])
        else:
            print("status      : %s" % job["status"])
        if job.get("failure_comment"):
            print("failure     : %s" % job["failure_comment"])
        print("pipeline    : %s" % job["pipeline"])
        print("tags        : %s" % str(job["tags"]))
        print("visibility  : %s" % job["visibility"])
        print("submit time : %s" % job["submit_time"])
        print("start time  : %s" % job["start_time"])
        print("end time    : %s" % job["end_time"])
    return 0


def handle_submit(proxy, options, config):
    prefix = ""
    if options.print_url:
        parsed = urlparse(options.uri)
        host = parsed.netloc.split("@")[-1]
        prefix = "%s://%s/scheduler/job/" % (parsed.scheme, host)

    for definition in options.definition:
        try:
            job_id = proxy.scheduler.jobs.submit(definition.read())
            if options.no_follow:
                if isinstance(job_id, list):
                    for job in job_id:
                        print(prefix + str(job))
                else:
                    print(prefix + str(job_id))
        except xmlrpc.client.Error as exc:
            print("Unable to submit %s: %s" % (definition.name, exc2str(exc)))

    if not options.no_follow:
        follow_logs(job_id, proxy, options, config)

    return 0


def handle_validate(proxy, options, _):
    ret = proxy.scheduler.jobs.validate(options.definition.read(), options.strict)
    if not ret:
        return 0
    print("key: %s" % ret["path"])
    print("msg: %s" % ret["msg"])
    return 1


def handle_wait(proxy, options, _):
    job = proxy.scheduler.jobs.show(options.job_id)
    old_state = ""
    time_elapsed = 0
    while job["state"] != "Finished":
        if old_state != job["state"]:
            if old_state:
                sys.stdout.write("\n")
            sys.stdout.write(job["state"])
        else:
            sys.stdout.write(".")
        sys.stdout.flush()
        old_state = job["state"]
        time.sleep(options.polling)
        job = proxy.scheduler.jobs.show(options.job_id)
        if options.timeout > 0:
            time_elapsed = time_elapsed + options.polling
            if time_elapsed > options.timeout:
                print("timeout!")
                return 1
    if old_state != job["state"] and old_state:
        sys.stdout.write("\n")
    return 0


def handle(proxy, options, config):
    handlers = {
        "cancel": handle_cancel,
        "config": handle_config,
        "definition": handle_definition,
        "list": handle_list,
        "logs": handle_logs,
        "queue": handle_queue,
        "resubmit": handle_resubmit,
        "run": handle_run,
        "show": handle_show,
        "submit": handle_submit,
        "validate": handle_validate,
        "wait": handle_wait,
    }
    return handlers[options.sub_sub_command](proxy, options, config)
