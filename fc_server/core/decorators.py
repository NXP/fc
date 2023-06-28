# -*- coding: utf-8 -*-
#
# Copyright 2021-2022 NXP
#
# SPDX-License-Identifier: MIT


import asyncio
import logging
from functools import wraps

logger = logging.getLogger("fc_server")


def safe_cache(func):
    @wraps(func)
    def decorator(*args):
        if args[2] not in args[0].__dict__[args[1]]:
            args[0].__dict__[args[1]][args[2]] = []
        return func(*args)

    return decorator


def check_priority_scheduler(*decorator_args):
    def wrapper(func):
        if asyncio.iscoroutinefunction(func):

            @wraps(func)
            async def async_decorator(*args):
                driver = args[0] if len(decorator_args) == 0 else decorator_args[0]
                if not driver.priority_scheduler:
                    return False
                return await func(*args)

            return async_decorator

        @wraps(func)
        def decorator(*args):
            driver = args[0] if len(decorator_args) == 0 else decorator_args[0]
            if not driver.priority_scheduler:
                return False
            return func(*args)

        return decorator

    return wrapper


def check_seize_strategy(*decorator_args):
    def wrapper(func):
        @wraps(func)
        def decorator(*args):
            driver = decorator_args[0]
            context = decorator_args[1]
            if not driver.framework_seize_strategies[context.__module__.split(".")[-1]]:
                return False
            return func(*args)

        return decorator

    return wrapper


def verify_cmd_results(func):
    @wraps(func)
    async def decorator(*args, desc=None):
        results, cmd_list = await func(*args, desc=desc)

        i = 0
        for result in results:
            device_update_response = result[1]
            if device_update_response != "":
                logger.error(cmd_list[i])
                logger.error(device_update_response)
                return False
            i += 1
        return True

    return decorator
