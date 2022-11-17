
import time

from .meta import MetaBase


def billable(key):
    def _billable(function):

        def __billable(*args, **kwargs):
            start_time = time.time()
            out = function(*args, **kwargs)
            execution_time = (time.time() - start_time) * 1000
            MetaBase().add_billable(key, execution_time)
            return out

        return __billable
    return _billable
