
import graphene
from .exceptions import RelatedTypeNotFound
from utils.core import rgetattr

from django.db.models import Model
from graphene_django.registry import get_global_registry


class ModelField(graphene.Dynamic):
    """Register a OneToOne or ForeignKey relationship in a custom (non-djangomodel) Schema"""
    def __init__(self, RelatedModel, **kwargs):
        def eval():
            registry = get_global_registry()
            Type = registry.get_type_for_model(RelatedModel)
            if not Type:
                raise RelatedTypeNotFound(f'Could not find a type for model {RelatedModel} in registry.', model=RelatedModel)
            return graphene.Field(Type, **kwargs)
        super(ModelField, self).__init__(eval)


class ModelListField(graphene.Dynamic):
    """Register a ManyToMany or OneToMany relationship in a custom (non-djangomodel) Schema"""
    def __init__(self, RelatedModel, **kwargs):
        def eval():
            registry = get_global_registry()
            Type = registry.get_type_for_model(RelatedModel)
            if not Type:
                raise RelatedTypeNotFound(f'Could not find a type for model {RelatedModel} in registry.', model=RelatedModel)
            return graphene.List(Type, **kwargs)
        super(ModelListField, self).__init__(eval)


class RelatedField:
    def __init__(self, related_name, RelatedType, related_alias=None, reverse_key=None):
        if not RelatedType:
            raise Exception('RelatedField must specify RelatedType.')
        if not related_name:
            raise Exception('RelatedField must specify a related name.')

        self.name = related_name
        self.Type = RelatedType
        self.related_alias = related_alias
        self.reverse_key = reverse_key

    def get_schema_name(self):
        return self.related_alias or self.name

    def __str__(self):
        if self.Type == 'self':
            return f'<{type(self).__name__} recursive to self on field {self.name} at 0x{id(self)}>'
        elif type(self.Type) == str:
            return f'<{type(self).__name__} string pointer to {self.Type} on field {self.name} at 0x{id(self)}>'
        return f'<{type(self).__name__} {self.Type.Meta.model.__name__}.{self.name} as {self.Type.__name__}.{self.related_alias or self.name} at 0x{id(self)}>'


# The Field classes are almost the same, but are distinguished for readability
class NestedField(RelatedField):
    def __init__(self, related_name, NestedType, related_alias=None, reverse_key=None):

        assert (type(NestedType) == type or NestedType == 'self'), f"NestedField Type type must be a type or string 'self'. Found {type(NestedType)}"
        assert isinstance(related_name, str), f"NestedField related name must be string. Found {type(related_name)}"

        if related_alias:
            assert isinstance(related_alias, str), f"NestedField related alias must be string. Found {type(related_alias)}"

        if reverse_key:
            assert isinstance(reverse_key, str), f"NestedField reverse key must be string. Found {type(reverse_key)}"

        return super(NestedField, self).__init__(
            related_name=related_name,
            RelatedType=NestedType,
            related_alias=related_alias,
            reverse_key=reverse_key
        )


# The different order of init attributes reflects the reverse nature of the relationship
class ReverseField(RelatedField):
    def __init__(self, ParentType, related_name, related_alias=None):

        # Asserts make sure the schema definition uses the correct format and types
        assert type(ParentType) == type, f"ReverseField Type type must be type. Found {type(ParentType)}"
        assert isinstance(related_name, str), f"ReverseField related name must be string. Found {type(related_name)}"

        if related_alias:
            assert isinstance(related_alias, str), f"ReverseField related alias must be string. Found {type(related_alias)}"

        return super(ReverseField, self).__init__(related_name, ParentType, related_alias)
