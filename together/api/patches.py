

from api.meta import meta_base

from funcy import monkey
from graphql.execution import executor
from promise.schedulers.immediate import ImmediateScheduler


"""
Monkey patches.

@monkey https://funcy.readthedocs.io/en/stable/objects.html#monkey

The decorator allows us to change the behaviour of a single method or class
in any library. This should only be used in extreme cases. It's fukin ugly.
"""


@monkey(executor)
def execute_fields(*args, **kwargs):
    """
    Sneaks TimeoutExit into graphql-core.

    Dependency: graphql-core==2.3.1

    Implants the meta_base.abort_request_if_timedout into graphql-core to
    timeout highly nested queries before they even get to qs evaluation.
    """
    meta_base.abort_request_if_timedout()  # this line is the only addition
    return execute_fields.original(*args, **kwargs)


@monkey(ImmediateScheduler)
def call(self, fn):
    """
    The original method suppresses BaseExceptions which breaks meta_base.abort_request_if_timedout.

    Dependency: promise==2.3
    """
    try:
        fn()
    except Exception:  # the only change, originally just a bare `except:`
        pass
