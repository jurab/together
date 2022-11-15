

from typing import Any, Dict, Type, TypeVar

from .core import inherit_from

from django import forms
from django.contrib import admin
from django.db import OperationalError, connection
from django.db.models import (
    Case,
    Field,
    IntegerField,
    Model,
    PositiveIntegerField,
    QuerySet,
    Value,
    When,
    Subquery,
    OuterRef,
)
from django.core.exceptions import ImproperlyConfigured
from django.db.models.aggregates import Count
from django.utils.deprecation import MiddlewareMixin


def fk_and_filter(qs, related_field, ids):
    """ForeignKey `AND` filter, returns only objects that have a relation to ALL ids at related field."""
    column_q = related_field + '__in'
    return qs.filter(**{column_q: ids}).annotate(obj_count=Count(related_field)).filter(obj_count=len(ids))


_T = TypeVar('T', bound=Model)


def dictionary_annotation(
    qs: QuerySet[_T],
    key_column_name: str,
    new_column_name: str,
    field_type: Type[Field],
    data_dict: Dict[Any, Any],
    default: Any = None,
) -> QuerySet[_T]:
    """Lookup a value in a dictionary based on a value in the DB for each object and annotate each separately in 1 query."""

    cases = [When(**{key_column_name: key, 'then': Value(data_dict.get(key, default))}) for key in data_dict.keys()]
    out = qs.annotate(
        **{new_column_name: Case(*cases, output_field=field_type(), default=default)}
    )

    return out


def case_order_qs(qs, prior_ordering, fields_lookups_values, exclude_no_case=False):
    """
    Order a qs by prior ordering and then case by case based on the fields_lookups_values.

    Example: first return items that start with a string, followed bu items that contain the string,
             followed by everything else. Pre-order by id.

             fields_lookups_values = [
                (field, 'startswith', search_string),
                (field, 'icontains', search_string),
             ]
    """
    reverse_enumerated_lookups = zip(reversed(range(len(fields_lookups_values))), fields_lookups_values)
    cases = [When(**{f"{field}__{lookup}": value}, then=Value(i + 1)) for i, (field, lookup, value) in reverse_enumerated_lookups]

    qs = qs.annotate(
        _searchresultpriority=Case(
            *cases,
            output_field=PositiveIntegerField(),
            default=0
        )
    ).order_by('-_searchresultpriority', prior_ordering)

    if exclude_no_case:
        qs = qs.exclude(_searchresultpriority=0)

    return qs


def sort_qs_by_ids(qs, ids):
    """Sort a queryset based on an iterable of ids."""
    cases = [When(pk=pk, then=sort_order) for sort_order, pk in enumerate(ids)]
    out = qs.annotate(sort_order=Case(*cases, output_field=IntegerField())).order_by('sort_order')

    return out


def has_reverse_relationship(obj):
    """Return true if object has any reverse relations."""
    obj_has_reverse = False
    if obj.id is not None:
        for reverse in [f for f in obj._meta.get_fields() if f.auto_created and not f.concrete]:
            name = reverse.get_accessor_name()
            has_reverse_one_to_one = reverse.one_to_one and hasattr(obj, name)
            has_reverse_other = not reverse.one_to_one and getattr(obj, name).count()
            if has_reverse_one_to_one or has_reverse_other:
                obj_has_reverse = True
    return obj_has_reverse


class DisableCsrfCheck(MiddlewareMixin):

    def process_request(self, req):
        attr = '_dont_enforce_csrf_checks'
        if not getattr(req, attr, False):
            setattr(req, attr, True)


class NoQuery:

    def __init__(self, msg='', allowed_count=0, strict=False, print_sql=False):
        self.msg = msg + ' '
        self.allowed_count = allowed_count
        self.strict = strict
        self.print_sql = print_sql

    def __enter__(self):
        self.start = len(connection.queries)
        return None

    def __exit__(self, _type, value, traceback):

        queries = connection.queries
        queries = [query for query in queries if 'silk_request' not in query['sql']]

        query_count = len(queries)

        msg = self.msg + f"{query_count - self.start}/{self.allowed_count} allowed queries sent."

        if self.start + self.allowed_count < query_count:
            if self.strict:
                raise OperationalError(msg)
            else:
                print(msg)
        return None


def print_admin_form_changes(form):
    data = []
    for name, field in form.fields.items():
        prefixed_name = form.add_prefix(name)
        data_value = field.widget.value_from_datadict(form.data, form.files, prefixed_name)
        if not field.show_hidden_initial:
            # Use the BoundField's initial as this is the value passed to
            # the widget.
            initial_value = form[name].initial
        else:
            initial_prefixed_name = form.add_initial_prefix(name)
            hidden_widget = field.hidden_widget()
            try:
                initial_value = field.to_python(hidden_widget.value_from_datadict(
                    form.data, form.files, initial_prefixed_name))
            except forms.ValidationError:
                # Always assume data has changed if validation fails.
                data.append(name)
                continue
        if field.has_changed(initial_value, data_value):
            print(name, data_value)


def clone_throughs(throughs, **kwargs):

    if not throughs:
        return

    to_remove = ['id']
    for key in kwargs.keys():
        if '_id' in key:
            to_remove += [key, key.replace('_id', '')]
        else:
            to_remove += [key, f'{key}_id']

    Model = throughs.model
    params = {'id': None, **kwargs}
    to_remove = {attr: None for attr in to_remove}

    for t in throughs:
        t.__dict__.update(**to_remove)
        for key, value in params.items():
            setattr(t, key, value)

    Model.objects.bulk_create(throughs)


def model_to_str(model):
    return '.'.join((model._meta.app_label, model._meta.object_name))


def get_ids(list_or_qs):
    if not list_or_qs:
        return set()

    if type(list_or_qs) == QuerySet:
        return set(list_or_qs.values_list('id', flat=True))

    try:
        return set(map(int, list_or_qs))  # items are int castable values
    except TypeError:
        return {int(getattr(item, 'id', None)) for item in list_or_qs}


def filter_ids_strict(ids, queryset):
    """Filter a queryset by id and raise an error if any of the ids don't exist."""
    out = queryset.filter(id__in=ids)
    if out.count() != len(ids):
        missing = get_ids(ids) - get_ids(out.values_list('id', flat=True))
        raise queryset.model.DoesNotExist(f"{queryset.model.__name__} {','.join(map(str, missing))} not found.")
    return out


def names_enum(*l):
    return ((item, item.replace('__', ' ').capitalize()) for item in l)


def custom_titled_filter(title):
    class Wrapper(admin.FieldListFilter):
        def __new__(cls, *args, **kwargs):
            instance = admin.FieldListFilter.create(*args, **kwargs)
            instance.title = title
            return instance
    return Wrapper


def has_annotation(qs, field):
    return field in qs.query.annotations


class DefaultFilter(admin.SimpleListFilter):

    def __init__(self, *args, **kwargs):
        out = super().__init__(*args, **kwargs)
        for attr in ('title parameter_name filter_field default_lookup other_lookups'.split()):
            if not hasattr(self, attr):
                raise ImproperlyConfigured(f"The list filter '{self.__class__.__name__}' does not specify a '{attr}'")
        return out

    def lookups(self, request, model_admin):
        return [
            ('all', 'All'),
            *names_enum(*self.other_lookups),
            (None, self.default_lookup.replace('__', ' ').capitalize()),

        ]

    def queryset(self, request, queryset):
        if self.value() == 'all': return

        value = self.default_lookup if not self.value() else self.value()
        value = value if '__' not in value else value.split('__')[1]

        return queryset.filter(**{self.filter_field: value})

    def choices(self, cl):
        for lookup, title in self.lookup_choices:
            yield {
                'selected': self.value() == lookup,
                'query_string': cl.get_query_string({
                    self.parameter_name: lookup,
                }, []),
                'display': title,
            }


class SubqueryAggregate(Subquery):
    template = '(SELECT %(function)s(_agg."%(column)s") FROM (%(subquery)s) _agg)'

    def __init__(self, queryset, column, output_field=None, **extra):
        if not output_field:
            # infer output_field from field type
            output_field = queryset.model._meta.get_field(column)
        super().__init__(queryset, output_field, column=column, function=self.function, **extra)


class SubquerySum(SubqueryAggregate):
    function = 'SUM'


class SubqueryAvg(SubqueryAggregate):
    function = 'AVG'


class SubqueryCount(Subquery):
    template = "(SELECT count(*) FROM (%(subquery)s) _count)"
    output_field = PositiveIntegerField()


def annotate_related_aggregate(qs, field, related_field, related_attribute, RelatedModel, function):
    sq = RelatedModel.objects.filter(**{related_field: OuterRef('id')})

    if function == 'count':
        SubqueryFunction = SubqueryCount
    else:
        class SubqueryFunction: pass
        SubqueryFunction.function = function
        SubqueryFunction = inherit_from(SubqueryFunction, SubqueryAggregate)

    return qs.annotate(**{field: SubqueryFunction(sq, related_attribute)})
