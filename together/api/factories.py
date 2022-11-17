

from .filters import FilterSet
from .meta import popmeta, meta_base
from .parsing import selection_from_info

from utils.string import camel_to_snake

from django.db.models import Prefetch
from graphql_jwt.decorators import login_required


def qs_resolver_factory(NodeType, single=False, source_fieldname=None):
    """
    Return a default Django qs resolver.

    Is by default applied during Django Model registration when using the @query decorator or defining nested fields with @node.
    Parameters are taken from the child Model's type definition.
    """

    def _get_relevant_fields_and_subpfs(NodeType, selection):
        """Extract fields asked for in the query and construct Prefetch objects for sub-selections."""
        sub_pfs = dict()
        relevant_fields = set()

        sub_selections = [s for s in selection.sub_selections if not hasattr(NodeType, f"resolve_{s.attribute}")]

        for sub_selection in sub_selections:
            attribute = NodeType.alias_to_attribute(sub_selection.attribute)
            relevant_fields.add(camel_to_snake(attribute))
            try:
                SubNodeType = NodeType.get_field_type(attribute)
                sub_pf = construct_qs(SubNodeType, sub_selection)
                sub_pfs[attribute] = sub_pf
            except AttributeError:
                # we hit a manually added field, so it's not on nested types
                pass

        return relevant_fields, sub_pfs

    def construct_qs(NodeType, selection, root=False):

        _ = selection.filters.pop('meta', None)  # popping the meta so it's not used as a filter parameter

        filters = getattr(NodeType.Meta, 'filters', {})
        filter_set = FilterSet(filters, **selection.filters)

        Model = NodeType.Meta.model
        qs = getattr(NodeType.Meta, 'queryset', Model.objects.all())

        relevant_fields, sub_pfs = _get_relevant_fields_and_subpfs(NodeType, selection)

        select_related = getattr(NodeType.Meta, 'select_related', [])
        select_related = [item for item in select_related if item in relevant_fields or item.split('__')[0] in relevant_fields]

        prefetch_related = getattr(NodeType.Meta, 'prefetch_related', [])
        # Prefetch related is either an iterable or a dictionary {schema_field: field_to_prefetch}
        prefetch_related = prefetch_related if type(prefetch_related) == dict else {item: item for item in prefetch_related}  # iterable -> dict
        # prefetch_related.update(sub_pfs)  # add Prefetch objects from _get_relevant_fields_and_subpfs  # TODO this breaks filtering of subfields when asked for twice on an object
        # Favour Prefetch objects over plain attribute names, because they might include further sub-prefetches
        prefetch_related = {attribute: prefetch for attribute, prefetch in prefetch_related.items() if prefetch not in prefetch_related.keys()}
        # Do not prefetch fields that are not mention by the query
        prefetch_related = [prefetch for attribute, prefetch in prefetch_related.items() if attribute in relevant_fields]

        # empty select_related would fetch all related fields!
        if select_related:
            qs = qs.select_related(*select_related)
        if prefetch_related:
            qs = qs.prefetch_related(*prefetch_related)

        qs = filter_set.apply(qs)

        meta_base.abort_request_if_timedout()  # can cause a TimeoutExit

        # The query should be fullfilled by a single request, all sub-selection should be its prefetches
        if root:
            out = qs
        else:
            attribute = NodeType.alias_to_attribute(selection.attribute)
            out = Prefetch(attribute, qs)
        return out

    def _resolve_child_qs(obj, ParentType, lookups):
        attribute = ParentType.alias_to_attribute(source_fieldname)
        qs = getattr(obj, attribute).all()

        if not lookups:
            return qs

        filters = getattr(NodeType.Meta, 'filters', {})
        filter_set = FilterSet(filters, **lookups)
        qs = filter_set.apply(qs)

        return qs

    @login_required
    @popmeta
    def qs_resolver(obj, info, **kwargs):

        NodeType = info.return_type.of_type.graphene_type
        ParentType = info.parent_type.graphene_type

        available_qs_lookups = dict(NodeType.get_lookups())
        available_filters = getattr(NodeType.Meta, 'filters', {})

        lookups = {key: value for key, value in kwargs.items() if key in available_qs_lookups or key in available_filters}

        selection = selection_from_info(info, lookups=lookups)

        if source_fieldname:
            return _resolve_child_qs(obj, ParentType, lookups)
        else:
            return construct_qs(NodeType, selection, root=True)

    return qs_resolver


def getattr_resolver_factory(attr):
    """Create a simple getattr resolver method with default return value None."""

    def getattr_resolver(obj, info):
        return getattr(obj, attr, None)

    return getattr_resolver
