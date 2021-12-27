from functools import wraps


def lava_safe_cache(func):
    @wraps(func)
    def decorator(*args):
        if args[2] not in args[0].__dict__[args[1]]:
            args[0].__dict__[args[1]][args[2]] = []
        func(*args)

    return decorator
