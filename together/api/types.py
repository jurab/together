from django.db import transaction
from django.db.models import Model as DjangoModel
from django.db.models.fields.related_descriptors import (
    ForwardManyToOneDescriptor,
    ForwardOneToOneDescriptor,
    ManyToManyDescriptor,
    ReverseManyToOneDescriptor,
)

import graphene

from api.exceptions import NodeNotFound
from utils.string import camel_to_snake

from .factories import getattr_resolver_factory, qs_resolver_factory
from .fields import NestedField, ReverseField


class ListActionEnum(graphene.Enum):
    ADD = 'add'
    CLEAN = 'clean'
    REMOVE = 'remove'
    SET = 'set'
    PUT = 'put'


class IDListInput(graphene.InputObjectType):
    action = ListActionEnum()
    ids = graphene.List(graphene.ID)


class BaseType:

    class Meta:
        abstract = True

    @classmethod
    def _get_filter_definitions(cls):
        filters = getattr(cls.Meta, 'filters', {})
        return {key: Filter.input for key, Filter in filters.items()}

    @classmethod
    def alias_to_attribute(cls, alias):
        for nested_field in cls.get_nested_fields():
            if alias in (nested_field.name, nested_field.related_alias):
                return nested_field.name
        return alias

    @classmethod
    def get_nested_field(cls, name):
        for nested_field in cls.get_nested_fields():
            if nested_field.name == name:
                return nested_field
        raise Exception(f'Could not find field {name} in type {cls.__name}')

    @classmethod
    def get_field_type(cls, field_name):
        return cls.get_nested_field(field_name).Type

    @classmethod
    def as_graphene_list(cls):
        assert hasattr(cls, '_meta')
        custom_filters = cls._get_filter_definitions()

        lookups = {**dict(getattr(cls.Meta, 'lookups', set())), **custom_filters}  # dictionary merge
        return graphene.List(cls, **lookups, description=getattr(cls.Meta, 'description', None))

    @classmethod
    def get_name(cls):
        name = getattr(cls.Meta, 'verbose', camel_to_snake(cls.__name__).replace('_type', ''))
        name = getattr(cls.Meta, 'verbose', None) or name + 's'
        return name

    @classmethod
    def add_field(cls, field, field_type, resolver=None):
        setattr(cls, field, field_type)
        if resolver:
            setattr(cls, f'resolve_{field}', resolver(field))

    @classmethod
    def _get_iterable_meta_attribute(cls, attribute):
        out = getattr(cls.Meta, attribute, [])
        if isinstance(out, dict):
            return tuple(out.items())
        return out

    @classmethod
    def get_nested_fields(cls):
        return [field for field in cls._get_iterable_meta_attribute('related_fields') if type(field) == NestedField]

    @classmethod
    def get_reverse_fields(cls):
        return [field for field in cls._get_iterable_meta_attribute('related_fields') if type(field) == ReverseField]

    @classmethod
    def get_lookups(cls):
        out = cls._get_iterable_meta_attribute('lookups')
        return out

    @classmethod
    def add_nested_field_to_meta(cls, *nested_fields):
        assert all([isinstance(nested_field, NestedField) for nested_field in nested_fields]), \
            f'Expected only NestedFields, received {[type(nested_field) for nested_field in nested_fields]}'
        cls.Meta.related_fields = getattr(cls.Meta, 'related_fields', set()) | set(nested_fields)

    @classmethod
    def set_description_meta(cls, description=None):
        setattr(cls.Meta, 'description', description)

    @classmethod
    def get_description(cls, description=None):
        if hasattr(cls.Meta, 'description'):
            return cls.Meta.description
        elif cls.__doc__:
            return cls.__doc__
        else:
            return cls.Meta.model.__doc__

    @classmethod
    def register_nested_field(cls, nested_field, resolver=None):
        from .registry import get_global_registry
        registry = get_global_registry()

        if nested_field.Type == 'self':
            nested_field.Type = cls
            NestedType = cls

        try:
            if type(nested_field.Type) == str:
                NestedType = registry.get_type_by_name(nested_field.Type)
            else:
                NestedType = registry.get_registered_type(nested_field.Type)
        except NodeNotFound as e:  # ignore this nested field/resolver if the nested Node is not registered (in tests)
            e.Type = nested_field.Type
            raise e

        if not NestedType:
            print(f"Related field {cls.__name__}.{nested_field.Type} not found during schema registration.")  # Should be changed to log WARNING
            return

        if type(NestedType) == str:
            nested_field.Type = registry.get_type_by_name(NestedType)
            NestedType = nested_field.Type

        lookups = dict(NestedType.Meta.lookups) if hasattr(NestedType.Meta, 'lookups') else {}
        custom_filters = NestedType._get_filter_definitions()
        lookups.update(custom_filters)
        name = nested_field.get_schema_name()

        if not resolver:
            is_m2m = type(getattr(cls.Meta.model, nested_field.name)) in (ManyToManyDescriptor, ReverseManyToOneDescriptor)
            if is_m2m:
                resolver = qs_resolver_factory(NestedType, source_fieldname=name)
            else:
                resolver = getattr_resolver_factory(nested_field.name)

        def dynamic_type():
            try:
                _type = registry.get_graphene_type(NestedType)
                assert _type
            except (KeyError, AssertionError):  # ignore this nested field/resolver if the nested Node is not registered (in tests)
                raise NodeNotFound(f"Nested field type {NestedType} not found in registry.", missing_type=NestedType)

            # We do this for a bug in Django 1.8, where null attr
            # is not available in the OneToOneRel instance
            null = getattr(nested_field, "null", True)

            if type(getattr(cls.Meta.model, nested_field.name)) in (ManyToManyDescriptor, ReverseManyToOneDescriptor):
                return graphene.List(_type, required=not null, resolver=resolver, **lookups)
            else:
                return graphene.Field(_type, required=not null, resolver=resolver, **lookups)

        setattr(cls, name, graphene.Dynamic(dynamic_type))

    @classmethod
    def save(cls, **kwargs):
        m2m_inputs = {}
        fk_inputs = {}

        with transaction.atomic():

            for key, value in kwargs.copy().items():
                field_name = cls.alias_to_attribute(key)
                field_type = type(getattr(cls.Meta.model, field_name))

                if field_type in (ManyToManyDescriptor, ReverseManyToOneDescriptor):
                    m2m_inputs[field_name] = kwargs.pop(key)

                if field_type in (ForwardManyToOneDescriptor, ForwardOneToOneDescriptor):
                    if not isinstance(kwargs[key], DjangoModel):
                        fk_inputs[field_name] = {'id': kwargs.pop(key)}

            # Replace Foreign Keys with actual Foreign Objects
            for field_name, data in fk_inputs.items():
                RelatedModel = getattr(cls.Meta.model, field_name).field.related_model
                kwargs[field_name] = cls._get_or_create_related_object(RelatedModel, data)

            # Create or Fetch an instance
            if not kwargs.get('id', None):
                cls.Meta.model(**kwargs).full_clean(exclude=['id'])
                instance = cls.Meta.model.objects.create(**kwargs)
            else:
                pk = kwargs.pop('id')
                instance = cls.Meta.model.objects.get(id=pk)
                if kwargs:
                    for key, val in kwargs.items():
                        setattr(instance, key, val)
                    instance.clean_fields()
                    instance.save()

            # Save M2M fields on the instance
            for field, action_item in m2m_inputs.items():
                cls._apply_m2m_action(instance, field, **action_item)

            return instance

    @classmethod
    def clear(cls, instance, field):
        manager = getattr(instance, field)

        try:
            manager.clear()
        except Exception as e:
            raise TypeError(f"Couldn't use {manager} to clear field. Original error: {e}")

    @classmethod
    def _get_or_create_related_object(cls, Model, data):
        if 'id' in data:
            if not data['id']:
                data.pop('id')
            return Model.objects.get(**data)
        else:
            return Model.objects.create(**data)

    @classmethod
    def _apply_m2m_action(cls, instance, field, action, data=None, ids=None):

        data = data or []

        if action not in 'clean add remove set':
            raise AttributeError(f'Unknown action: {action}')

        manager = getattr(instance, field)

        if action == 'clean':
            cls.clear(instance, field)
            return instance
        if action == 'set':
            cls.clear(instance, field)

        InputModel = manager.model

        # GET equivalent
        if ids:
            input_qs = InputModel.objects.filter(id__in=ids)
            if action in ('add', 'set'):
                manager.add(*input_qs)
                return instance._meta.model.objects.get(id=instance.id)
            if action == 'remove':
                manager.remove(*input_qs)
                return instance
            return instance

        # CREATE/UPDATE equivalent
        else:
            # TODO bulk create
            for kwargs in data:
                NestedField = cls.get_nested_field(field)
                NestedType = NestedField.Type
                if NestedField.reverse_key:
                    kwargs[NestedField.reverse_key] = instance

                child = NestedType.save(**kwargs)

                if action in ('add', 'set'):
                    manager.add(child)
                    continue
                if action == 'remove':
                    manager.remove(child)
                    continue
            return instance

    @classmethod
    def bulk_apply_m2m_action(cls, qs, field, action, related_ids=None):
        """
        Changes m2m relationships in bulk for a set of objects.

        Any operation will influence all objects of the `qs` on the `field` chosen.
        :param qs: the set of objects
        :param field: target m2m field
        :param action: what to do with the new objects: add, remove, set, clean
        :param related_ids: required for add/remove/set actions
        """
        manager = getattr(cls.Meta.model, field)
        Through = manager.through
        ids = qs.values_list('id', flat=True)

        related_name = manager.rel.model.__name__.lower()
        model_name = manager.rel.related_model.__name__.lower()

        if action not in ('clean set add remove'.split()):
            raise KeyError(f"The `action` of a bulk m2m operation has to be one of: clean, set, add, remove. Found '{action}'")

        if action != 'clean' and not hasattr(related_ids, '__iter__'):
            raise TypeError(f"`related_ids` iterable is required when doing add/remove/set bulk m2m actions. Found {related_ids}")

        if action in ('clean', 'set'):
            Through.objects.filter(**{f"{model_name}_id__in": ids}).delete()

        if action == 'clean':
            return

        if related_ids:

            if action in ('add', 'set'):
                throughs = []
                for pk in ids:
                    throughs += [Through(**{f"{model_name}_id": pk, f"{related_name}_id": related_id}) for related_id in related_ids]
                Through.objects.bulk_create(throughs)

            if action == 'remove':
                Through.objects.filter(**{f"{model_name}_id__in": ids, f"{related_name}_id__in": related_ids}).delete()

        return

    @classmethod
    def add_to_meta(cls, field, value):
        current = getattr(cls.Meta, field, [])

        if type(current) == dict:
            if type(value) == dict:
                new = {**current, **value}
            else:
                new = {**current, **{item: item for item in value}}
        elif type(current) == set:
            new = current | set(value)
        else:
            new = current + type(current)(value)
        setattr(cls.Meta, field, new)

    @classmethod
    def update_meta(cls, **kwargs):
        for key, value in kwargs.items():
            setattr(cls.Meta, key, value)
