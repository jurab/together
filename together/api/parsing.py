
from functools import reduce
from utils.core import rgetattr
from utils.misc import eval_or_none
from utils.string import camel_to_snake

from django.db.models import Q, QuerySet
from graphql.language.ast import Field, FragmentSpread, ListValue, Variable, ObjectValue


class Selection:
    """Represents a GrapQL selection or sub-selection."""
    def __init__(self, attribute, filters, sub_selections, alias=None):
        self.attribute = attribute
        self.filters = filters
        self.sub_selections = sub_selections
        self.alias = alias

    def _debug_print_body(self, depth=0):  # pragma: no cover
        t = ''.join(['  '] * depth)
        print(f'{t}{self.attribute} {self.filters}')
        for sub_selection in self.sub_selections:
            sub_selection._debug_print_body(depth + 1)

    def _debug_print(self):  # pragma: no cover
        self._debug_print_body(0)

    def has_field(self, name):
        if self.attribute == name:
            return True
        for sub_selection in self.sub_selections:
            if sub_selection.has_field(name):
                return True
        return False


def selection_from_info(info, lookups=None):
    return get_selection(info.operation.selection_set, info.variable_values, info.fragments, lookups=lookups, operation_name=info.path[0])


def get_selection(selection_set, variable_values=None, fragments=None, lookups=None, operation_name=None):

    def _argument_to_key_value_pair(argument):
        def _parse_object_value(fields):
            return {camel_to_snake(field.name.value): _argument_to_key_value_pair(field)[1] for field in fields}

        key = camel_to_snake(argument.name.value)

        if isinstance(argument.value, ListValue):
            if all(isinstance(value, ObjectValue) for value in argument.value.values):
                return key, [_parse_object_value(item.fields) for item in argument.value.values]
            return key, [item.value for item in argument.value.values]

        if isinstance(argument.value, Variable):
            return key, variable_values.get(argument.value.name.value, None)

        if isinstance(argument.value, ObjectValue):
            return key, _parse_object_value(argument.value.fields)

        else:
            return key, argument.value.value

    def _parse_filters(selection):
        key_value_pairs = [_argument_to_key_value_pair(argument) for argument in selection.arguments if argument.name.value != 'meta']
        key_value_pairs = [(key, value) for key, value in key_value_pairs if key and value is not None]
        filters = dict(key_value_pairs)
        return filters

    def _fragment_spread_to_fields(fragment_spread):
        """Fetch the fragment and return its field selection."""
        name = fragment_spread.name.value
        fragment = fragments.get(name)
        return fragment.selection_set.selections

    def _unpack_fragments(selections):
        """Get Fragment from a FragmentSpread and unpack its selection set."""
        selections = [[selection] if not isinstance(selection, FragmentSpread) else _fragment_spread_to_fields(selection) for selection in selections]
        return [item for sublist in selections for item in sublist]  # flatten

    def _parse_selection(selection):

        attribute = selection.name.value
        filters = _parse_filters(selection)
        alias = getattr(selection.alias, 'value', None)
        sub_selections = []

        if selection.selection_set:
            fields = selection.selection_set.selections
            fields = _unpack_fragments(fields)
            for field in fields:
                sub_selections.append(_parse_selection(field))

        return Selection(attribute, filters, sub_selections, alias=alias)

    for selection in selection_set.selections:
        if rgetattr(selection, 'alias.value', rgetattr(selection, 'name.value')) == operation_name:
            break  # we keep the `selection` variable that the loop breaks at
    else:
        selection = selection_set.selections[0]

    if type(selection) == Field and selection.selection_set:
        return _parse_selection(selection)

    raise ValueError('Error Parsing Query.')


def get_operation_name(info):
    """Parse operation name out of a graphene `info` object."""
    return info.path[0]


class DjangoLookup:
    """Represents a Django filter query attribute like strings such as `name_value__en__in=['apple', 'banana']`"""

    class Type:
        AND = 'and'
        OR = 'or'

    arguments = None
    operator = None

    def __init__(self, attr_string, operator=None, exclude=False):

        if not attr_string:
            return

        self.exclude = exclude

        if '&' in attr_string:
            arguments = [item.strip().split('=') for item in attr_string.split('&')]
            self.operator = DjangoLookup.Type.AND
        elif '|' in attr_string:
            arguments = [item.strip().split('=') for item in attr_string.split('|')]
            self.operator = DjangoLookup.Type.OR
        else:
            arguments = [attr_string.strip().split('=')]

        self.arguments = [(key, eval_or_none(value)) for key, value in arguments]

    def apply_to_qs(self, qs):
        if not self.arguments:
            return qs

        method = (QuerySet.filter, QuerySet.exclude)[self.exclude]

        if self.operator == self.Type.OR:
            def _or(a, b):
                return a | b
            return method(qs, reduce(_or, [Q(**dict([kwarg])) for kwarg in self.arguments]))

        elif self.operator == self.Type.AND:
            for kwarg in self.arguments:
                qs = method(qs, **dict([kwarg]))
            return qs

        return method(qs, **dict(self.arguments))
