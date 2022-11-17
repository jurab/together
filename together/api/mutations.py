import graphene

from collections import OrderedDict

from .converter import convert_django_field_to_input
from .fields import ModelField

from utils.core import inherit_from, copy_class
from core.string import camel_to_snake, decapitalize
from graphql_jwt.decorators import login_required


class Mutation:
    description = None

    class Arguments:
        pass

    class Meta:
        pass

    @classmethod
    def field(cls):
        arguments = cls.get_arguments()  # construct arguments if not specified manually on cls.Meta
        Out = copy_class(cls)
        Out.__name__ += 'Payload'
        Out = inherit_from(Out, graphene.Mutation, persist_meta=True)
        return Out.Field()

    @classmethod
    def get_schema_name(cls):
        return camel_to_snake(cls.__name__)

    @classmethod
    def get_arguments(cls):
        return getattr(cls.Meta, 'arguments', {})

    @classmethod
    def as_root_base(cls):
        if hasattr(cls, 'mutate'):
            class Mutation: pass
            setattr(Mutation, cls.get_schema_name(), cls.field())
            return Mutation
        return cls


class ModelMutation(Mutation):

    @classmethod
    def get_queryset(cls):
        return cls.get_type().Meta.queryset

    @classmethod
    def get_model_class(cls):
        return cls.Meta.model

    @classmethod
    def get_type(cls):
        from .registry import get_global_registry
        registry = get_global_registry()
        return registry.get_type_for_model(cls.get_model_class())

    @classmethod
    def get_field_model_class(cls, field_name):
        return cls.get_field_type(field_name).Meta.model

    @classmethod
    def get_field_type(cls, field_name):
        return cls.get_type().get_field_type(field_name)

    @classmethod
    def _construct_arguments_from_model(cls, exclude=None, include=None, extra=None):

        extra = extra or {}

        model_fields = cls.Meta.model._meta.get_fields()
        model_fields = sorted(model_fields, key=lambda field: hasattr(field, 'field'))  # move related descriptors to the end

        def get_field_name(field):
            if hasattr(field, 'field'):
                related_name = getattr(field, 'related_name', None)
                return related_name or f'{field.name}_set'
            else:
                return field.name

        arguments = OrderedDict([(get_field_name(field), convert_django_field_to_input(field)) for field in model_fields])
        arguments.update(extra)

        if include:
            exclude = set(arguments.keys()) - (set(include) | set(extra.keys()))

        if exclude:
            for key in exclude:
                arguments.pop(key, None)  # remove regardless if the key is in the arguments or not

        setattr(cls.Meta, 'arguments', arguments)

    @classmethod
    def get_arguments(cls):

        exclude = getattr(cls.Meta, 'exclude_arguments', None)
        extra = getattr(cls.Meta, 'extra_arguments', None)
        include = None

        if hasattr(cls.Meta, 'arguments'):

            if isinstance(cls.Meta.arguments, dict):
                return cls.Meta.arguments

            if type(cls.Meta.arguments) in (list, tuple):
                include = cls.Meta.arguments

        if exclude or include or extra or getattr(cls.Meta, 'arguments', '__all__') == '__all__':
            cls._construct_arguments_from_model(exclude=exclude, include=include, extra=extra)
        else:
            raise AttributeError('Mutation Meta needs to define one of: `arguments`: <(dict | [string])>, `exclude_arguments`: <[string]>')

        return cls.Meta.arguments


class Save(ModelMutation):
    description = 'Equivalent to UPDATE if id passed, else CREATE.'

    @classmethod
    def field(cls):
        setattr(cls, f'{decapitalize(cls.Meta.model.__name__)}', ModelField(cls.Meta.model))
        return super(Save, cls).field()

    @classmethod
    def mutate(cls, root, info, id=None, **kwargs):
        return cls.save(root, info, id, **kwargs)

    @classmethod
    def save(cls, root, info, id=None, **kwargs):
        Model = cls.get_model_class()
        model_name = decapitalize(Model.__name__)

        instance = cls.get_type().save(id=id, **kwargs)

        return cls(**{model_name: instance})


class Delete(ModelMutation):
    ok = graphene.Boolean()

    class Meta:
        arguments = {
            'id': graphene.ID(required=True)
        }

    @classmethod
    @login_required
    def mutate(cls, root, info, id, *args, **kwargs):
        cls.get_queryset().get(id=id).delete()
        return cls(ok=True)
