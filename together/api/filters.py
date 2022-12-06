import graphene
import re

from .parsing import DjangoLookup
from utils.core import inherit_from
from utils.misc import eval_or_none
from utils.string import camel_to_snake

from django.db.models import QuerySet


class PaginationFilter:
    class PaginationInput(graphene.InputObjectType):
        limit_to = graphene.Int(description="Limit the results to ``n``.")
        offset = graphene.Int(description="Offset the results by ``n``.")

    input = PaginationInput()

    def apply(self, qs, pagination_object):

        limit_to = int(pagination_object['limit_to']) if 'limit_to' in pagination_object else None
        offset = int(pagination_object['offset']) if 'offset' in pagination_object else None

        start = offset or 0
        if limit_to:
            return qs[start: limit_to + start]
        return qs[offset:]


class FilterSet:
    """Represents a set of filters for one GraphQL selection or sub-selection."""
    def __init__(self, filters, **kwargs):

        self.filters = filters  # {filter_name: filter_method}
        self.kwargs = kwargs

    def __str__(self):  # pragma: no cover
        return f"<Filter {self.filters}, {self.kwargs}>"

    def apply(self, qs):
        pagination = None

        for filter_field, Filter in self.filters.items():
            value = self.kwargs.pop(filter_field, None)

            # Save pagination as the last filter that applies
            if Filter == PaginationFilter:
                pagination = Filter, value
            else:
                qs = self._apply_single(qs, Filter, value)

        qs = qs.filter(**self.kwargs)

        if pagination:
            qs = self._apply_single(qs, *pagination)

        return qs

    def _apply_single(self, qs, Filter, value):

        if isinstance(value, str):
            try:
                value = eval_or_none(value)
            except (ValueError, SyntaxError):
                pass  # keep the value as a string
        if value is not None:
            qs = Filter().apply(qs, value)
            assert isinstance(qs, QuerySet), f'{Filter.__name__} return value needs to be a queryset. Got {type(qs)} instead.'

        return qs


class DjangoFilter:
    """
    Runs Django style data filtering.

    TODO multiple filters, AND/OR logic
    """
    class DjangoFilterInput(graphene.InputObjectType):
        filter = graphene.String(description="Django filter expression. Only returns objects fitting the filter. More info on lookups at \
            docs.djangoproject.com/en/2.2/ref/models/querysets/#id4")
        exclude = graphene.String(description="Django exclude expression. Excludes all objects fitting the filter. More info on lookups at \
            docs.djangoproject.com/en/2.2/ref/models/querysets/#id4")
        order_by = graphene.String(description="Single attribute or a tuple of attributes to sort the list by. Is evaluated as Python expression, \
            so simple strings need double quotes. \"'-example'\". `matchTo` automatically sorts by highest score, can be overriden, but `score` \
            can't be used for this field.")
        distinct = graphene.Boolean()

    input = DjangoFilterInput(description="""
        This enables a direct connection to the PostgreSQL
        database through Django lookups (i.e.: ``id__in=[1,2,3]``).

        The lookup string to have the format ``key1=lookup1&key2=lookup2``,
        where keys will be evaluated as a string and lookups as Python literals.
        Multiple lookups chain in and AND relationship.
        Allowing for inputting a list or a set of values.

        Ordering is done using the ``order_by`` field. Enter the order
        field in a snake_case and use ``-`` to reverse as in ``-order``.

        More on lookups in the Django `documentation`_.
        """)

    def apply(self, qs, kwargs):

        django_filter = DjangoLookup(kwargs.pop("filter", None))
        django_exclude = DjangoLookup(kwargs.pop("exclude", None), exclude=True)

        django_order_by = eval_or_none(kwargs.pop("order_by", None))
        django_distinct = kwargs.pop("distinct", False)

        if django_order_by and not re.match(r'^[_a-z0-9-]+$', django_order_by):
            raise Exception(f'DjangoFilter accepts only snake_case naming of fields, use {camel_to_snake(django_order_by)} instead of {django_order_by}.')

        qs = qs.filter(**kwargs)
        qs = django_filter.apply_to_qs(qs)
        qs = django_exclude.apply_to_qs(qs)

        if django_order_by:
            return qs.order_by(django_order_by)

        if django_distinct:
            qs = qs.distinct()

        return qs


class IDFilter:
    input = graphene.List(graphene.ID)

    def apply(self, qs, ids):
        return qs.filter(id__in=ids)


def enum_filter_factory(name, field, field_description):

    class Enum: pass
    Enum.__name__ = f"{name.title()}Enum"

    for key, value in field_description.items():
        setattr(Enum, key.capitalize(), key.lower())

    setattr(Enum, 'field_description', field_description)
    setattr(Enum, 'get_field_descriptions', lambda self: self.field_description.get(self.name))
    setattr(Enum, 'description', property(lambda self: self.get_field_description()))

    Enum = inherit_from(Enum, graphene.Enum)

    class Filter: pass
    Filter.__name__ = f"{name.title()}Filter"

    setattr(Filter, 'input', Enum())
    setattr(Filter, 'apply', lambda self, qs, value: qs.filter(**{'field': value}))

    return Filter
