import time
from threading import local

from django.conf import settings

from utils.core import Singleton
from utils.string import camel_to_snake

from .exceptions import TimeoutExit


"""
Meta

Purpose:
    1) handle anonymised end-user context in a form of attributes. i.e. language, diets, age...
    2) incorporate this context as a part of the schema for readability
    3) handle different context for each operation run in a single graphql query (support multiple operations)
"""

def popmeta(function):
    """Pops a `meta` payload from the functions kwargs and sets it."""
    def _popmeta(*args, **kwargs):
        meta_payload = kwargs.pop('meta', None)
        if meta_payload:
            meta_payload = {camel_to_snake(key): value for key, value in meta_payload.items()}
            set_meta(**meta_payload)
        return function(*args, **kwargs)
    return _popmeta


class MetaBase(local, metaclass=Singleton):
    """
    Meta base class.

    MetaBase holds a single QueryMeta per graphene operation in a single request.
    """

    _query_meta_dict = {}
    _active_query = None
    cache_key_prefix = None
    warnings = []

    def __init__(self):
        self._query_meta_dict['default'] = QueryMeta()
        self._start_time = time.time()

    def to_dict(self):
        return [{
            'operation': operation,
            'user': m.user
        } for operation, m in self._query_meta_dict.items()]

    def add_meta(self, query_name, meta):
        self._query_meta_dict[query_name] = meta

    def get_meta(self):
        try:
            return self._query_meta_dict.get(self._active_query, self._query_meta_dict['default'])
        except KeyError:
            self._query_meta_dict['default'] = QueryMeta()
            return self._query_meta_dict['default']

    def activate_query(self, query_name):
        if query_name not in self._query_meta_dict:
            raise KeyError(f"Meta activation error, cannot find meta for operation: {query_name}.")
        self._active_query = query_name

    def active_query(self):
        return self._active_query

    def execution_time(self):
        return (time.time() - self._start_time) * 1000

    def abort_request_if_timedout(self):
        """
        Aborts the whole request if the time runs out.

        Can raise TimeoutExit - same level as exit(),
        so make sure the exception get caught somewhere,
        otherwise graphene can't deal with it and the
        response hangs.
        """
        if self.execution_time() > settings.GRAPHQL_TIMEOUT:
            raise TimeoutExit()

    def reset_execution_time(self):
        self._start_time = time.time()

    def reset(self):
        self._query_meta_dict = {}
        self._active_query = None
        self._query_meta_dict['default'] = QueryMeta()
        self.reset_execution_time()
        self.cache_key_prefix = None
        self.warnings = []

    def add_warning(self, warning):
        self.warnings.append(warning)

    def get_warnings(self):
        return self.warnings


class QueryMeta:
    user = None
    _query_name = None

    def __init__(self, *args, **kwargs):
        self.set_all(*args, **kwargs)

    def __str__(self):
        return f"<QueryMeta {self._full_string_representation()}>"

    def __repr__(self):
        return str(self)

    def full_string_representation(self):
        """Used for hash creation in cache keys, needs to reflect all attributes of the Meta"""
        user_repr = f'({self.user.id})' if self.user else ''
        return f"Meta {user_repr}: {self._query_name}"

    def set_all(self, user=None, query_name='default'):
        self._query_name = query_name


def get_meta():
    return MetaBase().get_meta()


def reset_meta():
    MetaBase().reset()


def set_meta(*args, **kwargs):
    get_meta().set_all(*args, **kwargs)


class MetaShortcut:
    def __getattribute__(self, name):
        return getattr(get_meta(), name)

    def __setattr__(self, name, value):
        set_meta(**{name: value})


meta = MetaShortcut()
meta_base = MetaBase()

# apply patches needed for MetaBase.abort_request_if_timedout to work
from .patches import call, execute_fields
