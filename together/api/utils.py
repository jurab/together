import hashlib

from .meta import MetaBase
from utils.core import rgetattr

from cachalot.utils import get_query_cache_key


def is_root_info(info):
    root_path = info.path[0]
    info_path = rgetattr(info.field_asts[0], 'alias.value', info.field_asts[0].name.value)
    return root_path == info_path


class Locked(Exception):
    message = "The object is locked from adding new nodes."


def lockable(function):
    """Give a class attribute `locked` and decorate its methods to prevent usage."""
    def _lockable(*args, **kwargs):
        if getattr(args[0], 'locked', False):
            raise Locked(f"{args[0]} is locked.")
        return function(*args, **kwargs)
    return function


class LockableDict(dict):
    """Dictionary that can be switched to `locked`, preventing new items to be added."""

    _locked = False

    class DictionaryLocked(Exception):
        message = "This dictionary is locked from adding new items."

    def __default_setitem(self, key, value):
        return super().__setitem__(key, value)

    def __locked_setitem(self, key, value):
        if key not in self:
            raise self.DictionaryLocked
        else:
            return self.__default_setitem(key, value)

    def lock(self):
        self._locked = True

    def unlock(self):
        self._locked = False

    def __setitem__(self, key, value):
        return (self.__default_setitem, self.__locked_setitem)[self._locked](key, value)


def query_cache_key(*args, **kwargs):
    """
    Prepend default cachalot key with a prefix hash.

    The prefix hash is made from the tenant id and roles.
    It is saved on MetaBase to be quickly available during the whole request.
    """

    hash_string = get_query_cache_key(*args, **kwargs)

    user, tenant, roles, as_superuser = context.get_context()

    if not tenant or as_superuser:
        return hash_string

    if not MetaBase().cache_key_prefix:
        # Should only run a single time
        prefix = f'{tenant.pk}_{str(",".join(roles))}'
        MetaBase().cache_key_prefix = prefix

    hash_string = MetaBase().cache_key_prefix + hash_string
    hash_string = hashlib.sha256(bytes(hash_string, encoding='utf-8')).hexdigest()

    return hash_string
