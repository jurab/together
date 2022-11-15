
import inspect

from functools import reduce
from collections import Counter, OrderedDict
from copy import copy
from itertools import groupby
from typing import Any, Callable, Dict, Iterable, Sequence, Tuple


def duple(d, keys):
    """Return a tuple of dictionary values based on keys."""
    return (d[key] for key in keys)


def rgetattr(obj, attr, *args):
    """
    Recursive getattr function.
    """
    def _getattr(obj, attr):
        return getattr(obj, attr, *args)
    return reduce(_getattr, [obj] + attr.split('.'))


def rget(obj, attr, *args):
    """
    Recursive getattr function.
    """
    def _get(obj, attr):
        return None if not obj else obj.get(attr, *args)
    return reduce(_get, [obj] + attr.split('.'))


def where(iterable, default=None, **conditions):
    """For condition a=1 return the first item in iterable where item.a==1."""
    conditions = {key.replace('__', '.'): val for key, val in conditions.items()}
    for item in iterable:
        for attr, val in conditions.items():
            if rgetattr(item, attr, None) != val:
                break
        else:
            return item

    return default


def aggregate_to_dict(
    values: Sequence[Tuple[Any, ...]], idx: int, fnc: Callable[..., Any] = sum
) -> Dict[Any, Any]:
    """
    Takes a list of lists, groups by idx and aggregates by fnc

    Example: [('a', 1, 10), ('b', 2, 3), ('a', 2, 20)] -> {'a': [3, 30], 'b': [2, 3]}
    """
    index_function = lambda x: x[idx]
    if len(values[0]) == 2:  # We assume all values have same length
        return {key: fnc(item[1] for item in group) for key, group in groupby(
            sorted(values, key=index_function), key=index_function
        )}

    indices = list(range(len(values[0])))
    indices.pop(idx)
    grouped = {key: [[item[i] for i in indices] for item in group] for key, group in groupby(
        sorted(values, key=index_function), key=index_function
    )}

    return {key: [fnc(item[i] for item in group) for i in range(len(group[0]))] for key, group in grouped.items()}


def group_by(data, attribute):
    """Return a dictionary {attribute_value: object_with_attribute} (attribute can be recursive `foo.bar.fam`)"""

    if type(attribute) == str and '.' not in attribute:
        return groupby(data, attribute)

    def _get_final_attribute(item, attributes):
        attributes = attributes.split('.')
        out = getattr(item, attributes[0])

        for attribute in attributes[1:]:
            out = getattr(out, attribute)
        return out

    out = OrderedDict()

    for item in data:
        if type(attribute) == str:
            key = _get_final_attribute(item, attribute)
            out[key] = out.get(key, []) + [item]
        if type(attribute) == int:
            key = item[attribute]
            item = item[:attribute] + item[attribute + 1:]
            out[key] = out.get(key, []) + [item]
    return out


def get_index_or_default(item, order, default=9999):
    try:
        return order.index(item)
    except ValueError:
        return default


def inherit_from(Child, Parent, persist_meta=False):
    """Return a class that is equivalent to Child(Parent) including Parent bases."""
    PersistMeta = copy(Child.Meta) if hasattr(Child, 'Meta') else None

    if persist_meta:
        Child.Meta = PersistMeta

    # Prepare bases
    child_bases = inspect.getmro(Child)
    parent_bases = inspect.getmro(Parent)
    bases = tuple([item for item in parent_bases if item not in child_bases]) + child_bases

    # Construct the new return type
    try:
        Child = type(Child.__name__, bases, Child.__dict__.copy())
    except AttributeError as e:
        if str(e) == 'Meta':
            raise AttributeError('Attribute Error in graphene library. Try setting persist_meta=True in the inherit_from method call.')
        raise e
    except TypeError as e:
        e.message = f"Likely a meta class mismatch. {type(Child)} and {type(Parent)} not compatible for inheritance."
        raise e

    if persist_meta:
        Child.Meta = PersistMeta

    return Child


def get_method_parent_class(meth):
    for cls in inspect.getmro(meth.im_class):
        if meth.__name__ in cls.__dict__:
            return cls
    return None


def copy_class(TargetClass, with_bases=True):
    """Copy class either as a complete equivalent, or create a class with exactly the same attributes, but no bases by with_bases=False."""
    return type(TargetClass.__name__, TargetClass.__bases__ if with_bases else tuple(), dict(TargetClass.__dict__.items()))


def match_type_to(to_mutate, to_apply):
    return type(to_apply)(to_mutate)


def flatten(l):
    if l is None:
        return None
    return [item for sublist in l for item in sublist]


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def color_string(string, colors):
    return reduce(lambda a, b: a + b, colors) + string + Colors.END


def colored_print(string, colors):
    print(color_string(string, colors))


def debug_print_conditions(message='', **kwargs):
    out = [color_string(name, [Colors.RED, Colors.GREEN][condition]) for name, condition in kwargs.items()]
    print(message, *out)


def get_duplicates(iterable):
    return [item for item, count in Counter(iterable).items() if count > 1]


def validate_unique(iterable):
    duplicate_keys = get_duplicates([key for key, value in iterable])
    if duplicate_keys:
        raise KeyError(f'Duplicate keys found in {type(iterable)}: {", ".join(duplicate_keys)}')


def sceround(pkscores: Iterable[Tuple[Any, float]], precision=3):
    i = 10**precision
    return [(a, round(b * i) / i)for a, b in pkscores]


def round_or_none(number, decimal_places):
    return round(number, decimal_places) if number else None
