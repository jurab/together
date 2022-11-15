

import pprint
import re
from textwrap import indent as indent_fn
from typing import Sequence


def decapitalize(string):
    return string[0].lower() + string[1:]


def camel_to_snake(camel):
    out = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', camel)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', out).lower()


def align_string(s, n):
    s = s + ' ' * (n - len(s))
    return s[:n]


def logfmt(obj, indent=0, no_sort=False) -> str:
    """Used for prettyprinting in logs.
    Custom indentation of output can be specified with indent param.
    If set or Sequence is passed as obj it will be sorted.
    """
    if isinstance(obj, (set, frozenset, Sequence)):
        if no_sort:
            obj = list(obj)
        else:
            obj = sorted(obj)
    return indent_fn(pprint.pformat(obj, compact=True), ' ' * indent)
