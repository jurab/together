
from collections.abc import Iterable

from .exceptions import MetaConfigurationError


def validate_type_meta(TargetType):

    if not hasattr(TargetType.Meta, 'model'):
        raise MetaConfigurationError(f'{TargetType}.Meta has no attribute model.')

    if not hasattr(TargetType.Meta, 'fields'):
        raise MetaConfigurationError(f'{TargetType}.Meta has no attribute fields.')

    if hasattr(TargetType.Meta, 'lookups'):
        lookup_tuples = None
        if isinstance(TargetType.Meta.lookups, dict):
            lookup_tuples = TargetType.Meta.lookups.items()
        elif isinstance(TargetType.Meta.lookups, Iterable):
            lookup_tuples = TargetType.Meta.lookups
        else:
            raise MetaConfigurationError(f'{TargetType}.Meta.lookups has to be a dict or an iterable.')

        if not all([type(attr_name) == str for attr_name, value in lookup_tuples]):
            raise MetaConfigurationError(f'{TargetType}.Meta.lookups keys have to be strings.')

        if not all([hasattr(value, 'Field') for attr_name, value in lookup_tuples]):
            raise MetaConfigurationError(f'{TargetType}.Meta.lookups values have to be graphene Types.')
