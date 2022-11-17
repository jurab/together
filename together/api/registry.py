import graphene
import inspect

from functools import reduce
from pydoc import locate

from .exceptions import NodeNotFound
from .factories import qs_resolver_factory, getattr_resolver_factory
from .fields import NestedField
from .meta import popmeta
from .types import BaseType  # QueryMeta as QueryMetaInput
from .utils import lockable
from .validators import validate_type_meta

from utils.core import inherit_from, Singleton, rgetattr
from utils.string import camel_to_snake

from django.db.models import Model
from graphene_django.registry import reset_global_registry
from graphene_django.types import DjangoObjectType


def register_type(typename=None):
    """
    Make registering a model with GraphQL easy.

    Automatically inherits from DjangoObjectType and registers attributes and their resolvers based on Type Meta class.

    Meta class options including defaults:

    model: Target model class.
    fields: An iterable of field names to register.
    related_fields: Iterable of types NestedField and ReverseField
    lookups: Iterable of tuples of filter attributes and their types (only primitive types).
    filters: Iterable of tuples of custom filter name and filter class
    prefetch: Fields to prefetch.
    select_related: Fields to apply select_related to.
    """

    def _register(TargetType):
        if type(TargetType) != type:
            raise TypeError(f"Registered Type must be a class, found {type(TargetType)}")
        TargetType = get_global_registry().register_type(TargetType, typename)
        return TargetType

    return _register


def register_mutation(TargetMutation):
    """
    Make registering a mutation with GraphQL easy.

    Automatically inherits from graphene.Mutation and registers attributes and their resolvers based on Type Meta class.

    Meta class can be defined either standard graphene way, or it can specify an object_type attribute, which points
    the registration process to that Type and allows you to specify arguments as '__lookups__', taking the mytation
    arguments from the Type.
    """
    TargetMutation = get_global_registry().register_mutation(TargetMutation)
    return TargetMutation


def get_schema(subscription=None):
    """Return api schema, construct it if it doesn't exist yet."""
    return get_global_registry().get_schema(subscription)


def reset_schema():
    """Reset both graphene and api registry."""
    reset_global_registry()
    get_global_registry()


def get_global_registry():
    """Return Registry singleton instance."""
    return Registry()


def reset_global_registry():
    """Delete the Registry singleton instance."""
    Registry().reset()


class RegisteredNode:
    """
    Single registered node (type).

    Representation of a Type registered as a Node of the schema graph.
    :attr typename: Name of the type to be used in the schema. Set by the register decorator @register_query(typename)
    :attr Type: Type of the node
    :attr GrapheneType: Type that already inherited from graphene.ObjectType
    """
    typename = None
    Type = None
    GrapheneType = None

    def __str__(self):
        return(f"<Node {self.typename}: {self.Type}({self.model})>")

    def __repr__(self):
        return str(self)

    def __init__(self, Type, typename=None, GrapheneType=None):
        self.Type = Type
        self.typename = typename or Type.__name__
        self.GrapheneType = GrapheneType

    def __eq__(self, other):
        """Two registered Nodes are in conflict if either their typename, type or model are the same."""

        if self.Type == other.Type or self.GrapheneType == other.GrapheneType or self.typename == other.typename:
            return True
        if self.is_model_node and other.is_model_node and self.Type.Meta.model == other.Type.Meta.model:
            return True
        return False

    def __hash__(self):
        if self.is_model_node:
            return hash(self.Type.Meta.model)
        else:
            return hash(self.Type)

    @property
    def model(self):
        return rgetattr(self.Type, 'Meta.model', None)

    @property
    def is_model_node(self):
        if isinstance(self.Type, BaseType):
            return True
        return hasattr(self.Type, 'Meta') and hasattr(self.Type.Meta, 'model')


class NodeSet(set):
    """A set of nodes addressable by Type."""

    def __getitem__(self, Type):
        for node in self:
            if node.Type == Type:
                return node
        raise KeyError(f"Type {Type} not found in the NodeSet.")

    def update_type(self, Type):
        self[Type].Type = Type

    def add(self, item):
        assert type(item) == RegisteredNode, "You can only add type RegisteredNode into Registry NodeSet."
        return super().add(item)

    def add_graphene_type(self, Type, GrapheneType):
        self[Type].GrapheneType = GrapheneType
        self.GrapheneType = GrapheneType

    def __setitem__(self, key, item):
        if key not in self:
            raise KeyError()
        return super().__setitem__(key, item)


class Registry(metaclass=Singleton):
    DEBUG_PRINT = False

    mutations = []
    nodes = NodeSet()
    schema = None
    _locked = False  # locked from adding new types

    input_registry = {}
    list_input_registry = {}

    class Query:
        @classmethod
        def register_node(cls, NodeType):

            node_name = NodeType.get_name()
            node_list = NodeType.as_graphene_list()

            resolver_name = f'resolve_{node_name}'
            resolver = qs_resolver_factory(NodeType)

            setattr(cls, node_name, node_list)
            setattr(cls, resolver_name, resolver)

        @classmethod
        def _reset_attributes(cls):
            to_delete = []
            for key in Registry.Query.__dict__.keys():
                if key[0] == '_' or key == 'register_node':
                    continue
                else:
                    to_delete.append(key)
            for key in to_delete:
                delattr(cls, key)

    class Mutation:
        pass

    def __init__(self, *args, **kwargs):
        self.mutations = []
        self.nodes = NodeSet()
        self.schema = None

    def _lock(self):
        """Lock to not allow adding nodes."""
        self._locked = True

    def _unlock(self):
        """Unlock to allow adding nodes."""
        self._locked = False

    @lockable
    def add_node(self, Type, typename=None, GrapheneType=None):
        self.nodes.add(RegisteredNode(Type=Type, typename=typename, GrapheneType=GrapheneType))

    def get_model_nodes(self):
        return {node for node in self.nodes if node.is_model_node}

    def get_custom_nodes(self):
        return {node for node in self.nodes if not node.is_model_node}

    def get_type(self, model=None, Type=None, typename=None, include_custom=True):
        """Universal type get based on - Schema name, Type or Django model (also accepts strings)."""
        nodes = (self.get_model_nodes(), self.get_custom_nodes())[include_custom]

        if Type:
            assert isinstance(Type, type), f"Schema Type type must be type. Found {Type} of type {type(Type)}"
        if typename:
            assert isinstance(typename, str), f"Schema typename must be string. Found {typename} of type {type(typename)}"
        if model:
            assert Model in model.mro(), f"Schema model must be Django model. Found {model} of type {type(model)}"

        for node in nodes:
            if any((
                model and node.model == model,
                typename and node.typename == typename,
                typename and node.Type.__name__ == typename,
                Type and node.typename == Type,
                Type and node.Type == Type,
                Type and node.model == rgetattr(Type, 'Meta.model', ''),
                Type and node.Type.__name__ == Type,
                Type and node.Type.__name__ == getattr(Type, '__name__', ''),
                Type and node.GrapheneType == Type
            )):
                return node.Type

        msg = f'egistry.get_type(model={repr(model)}, Type={repr(Type)}, typename={repr(typename)}, include_custom={repr(include_custom)})'
        Type = Type or typename or model.__name__
        raise NodeNotFound(msg, Type)

    # Shortcuts to above get_type for readability
    def get_graphene_type(self, Type):
        return self.nodes[Type].GrapheneType

    def get_type_for_model(self, model):
        return self.get_type(model=model, include_custom=False)

    def get_type_by_name(self, typename):
        return self.get_type(typename=typename, include_custom=False)

    def get_registered_type(self, Type):
        return self.get_type(Type=Type, include_custom=False)

    def get_schema(self, subscription=None):
        """Construct schema if it doesn't exist and return existing/created one."""
        if not self.schema:
            self._construct_schema(subscription)
        return self.schema

    def reset(self):
        """Remove all nodes, mutation and the existing schema."""
        self.mutations = []
        self.nodes = NodeSet()
        self.schema = None
        self.Query._reset_attributes()

    def register_mutation(self, TargetMutation):
        """Add a Mutation to attach it to the Root Mutation."""
        self.mutations += [TargetMutation]
        return TargetMutation

    def register_type(self, TargetType, typename=None):
        """Add a Type to attach it to the Root Query."""
        is_django_schema = hasattr(TargetType, 'Meta') and hasattr(TargetType.Meta, 'model')
        TargetType = self._register_django_type(TargetType, typename) if is_django_schema else self._register_custom_type(TargetType, typename)
        return TargetType

    def _construct_schema(self, subscription=None):
        """Force all registered schemas and mutations to inherit from graphene object types and return graphene.Schema."""
        Query = self._construct_root_query()
        Mutation = self._construct_root_mutation() if self.mutations else None
        self.schema = graphene.Schema(query=Query, mutation=Mutation, subscription=subscription)

    def _construct_root_mutation(self):
        """Return a graphene.Mutation class with all the registered mutations attached as attributes."""

        bases = [self.Mutation] + [NodeMutation.as_root_base() for NodeMutation in self.mutations] + [graphene.ObjectType]
        return reduce(lambda Mutation, NodeMutation: inherit_from(Mutation, NodeMutation, persist_meta=True), bases)

    def _construct_root_query(self):
        """Return a graphene.ObjectType class with all the registered nodes attached as attributes."""

        if not self.get_model_nodes():
            raise Exception('No registered types found during schema creation.')

        self._tranform_reverse_to_nested_fields()  # Make reverse fields into nested fields on the referenced Nodes
        self._register_nested_types()
        self._lock()  # prevent the nodes to be changed from now
        self._attach_nodes()  # Construct nested fields into Node attributes and attach them to Query
        Query = inherit_from(self.Query, graphene.ObjectType)  # Initialize as a Graphene object, can't change attributes after this

        return Query

    def _register_nested_types(self):
        nested_fields = []

        for node in self.get_model_nodes():
            nested_fields += node.Type.get_nested_fields()

        for nested_field in nested_fields:
            if not isinstance(nested_field.Type, str):
                self.register_type(nested_field.Type)

    def _tranform_reverse_to_nested_fields(self):
        """
        Add all the reverse access to nested fields of the parent classes.

        (reverse_access to Tag on IngredientType needs to become a nested_field on TagType)
        """
        for node in self.get_model_nodes():

            for reverse_field in node.Type.get_reverse_fields():

                ReverseType = self.get_type(Type=reverse_field.Type, include_custom=False)

                if not ReverseType:
                    raise Exception(f'Could not find {ReverseType.__name__} in registered Types.')
                else:
                    self.nodes[ReverseType].Type.add_nested_field_to_meta(NestedField(reverse_field.name, node.Type, reverse_field.related_alias))

    def _attach_nodes(self):
        """Attach all registered Types to the Query as attributes."""

        nodes = sorted(self.get_model_nodes(), key=lambda node: node.typename)
        for node in nodes:

            # Attach nested fields and their resolvers to the Type
            for nested_field in node.Type.get_nested_fields():
                node.Type.register_nested_field(nested_field, resolver=getattr(node.Type, f'resolve_{nested_field.name}', None))

            node.Type.__name__ = node.typename  # setup for graphene
            node.Type.Meta.name = node.typename  # setup for graphene
            GrapheneType = inherit_from(node.Type, DjangoObjectType, persist_meta=True)

            assert hasattr(GrapheneType, '_meta')

            self.nodes.add_graphene_type(node.Type, GrapheneType)
            self.Query.register_node(GrapheneType)

        for node in self.get_custom_nodes():

            NodeType = node.GrapheneType

            if hasattr(NodeType, 'resolve'):

                NodeType.resolve = popmeta(NodeType.resolve)

                name = camel_to_snake(node.typename)
                assert callable(NodeType.resolve), f'{NodeType}.resolve has to be a callable.'

                if hasattr(NodeType, 'Meta') and hasattr(NodeType.Meta, 'arguments'):
                    setattr(
                        self.Query,
                        name,
                        graphene.Field(
                            NodeType,
                            # meta=QueryMetaInput(description="Operation wide end-user context."),
                            description=NodeType.__doc__,
                            **NodeType.Meta.arguments
                        )
                    )
                else:
                    setattr(
                        self.Query,
                        name,
                        graphene.Field(
                            NodeType,
                            # meta=QueryMetaInput(description="Operation wide end-user context."),
                            description=NodeType.__doc__
                        )
                    )

                setattr(self.Query, f'resolve_{name}', NodeType.resolve)

    def _register_custom_type(self, TargetType, typename=None):
        """Register a non-model type."""
        if not hasattr(TargetType, 'Meta'):
            class Meta: pass
            setattr(TargetType, 'Meta', Meta)

        GrapheneType = inherit_from(TargetType, graphene.ObjectType, persist_meta=True)

        self.add_node(TargetType, typename, GrapheneType=GrapheneType)

        return TargetType

    def merged_meta_data(self, meta_a, meta_b, typename=None):
        """
        Merge 2 Type Meta classes.

        This is important for inheritance between Schemas and to allow
        schema mixins. A schema mixin will add fields, prefetches, lookups
        and other Meta attributes that we need to combine with the Meta
        class of the child Schema without overwritting anything.
        """

        def _merge_iterables(attribute):
            return set(getattr(meta_a, attribute, [])) | set(getattr(meta_b, attribute, []))

        def _merge_dicts(attribute):

            return {
                **dict(getattr(meta_a, attribute, {})),
                **dict(getattr(meta_b, attribute, {}))
            }

        attrs = {
            'fields': list(_merge_iterables('fields')),
            'extra_fields': _merge_iterables('extra_fields'),
            'related_fields': _merge_iterables('related_fields'),
            'select_related': list(_merge_iterables('select_related')),
            'prefetch_related': _merge_iterables('prefetch_related'),
            'filters': _merge_dicts('filters'),
            'lookups': _merge_dicts('lookups'),
        }

        # Keep the '__all__' symbol instead of any specific iterable
        if getattr(meta_a, 'fields', None) == '__all__' or getattr(meta_b, 'fields', None) == '__all__':
            attrs['fields'] = '__all__'

        return attrs

    def _register_django_type(self, TargetType, typename=None):
        """Register a model type."""

        TargetType = inherit_from(TargetType, BaseType, persist_meta=True)

        validate_type_meta(TargetType)
        TargetType.set_description_meta(description=TargetType.get_description())

        base_pf = getattr(TargetType.Meta, 'prefetch_related', dict())
        base_sr = getattr(TargetType.Meta, 'select_related', dict())

        # Transform prefetch and select related from iterable to a dict
        # the dict format allows us to say "prefetch field <a> if a non-model field is called"
        if type(base_pf) != dict:
            TargetType.Meta.prefetch_related = {item: item for item in base_pf}

        if type(base_sr) != dict:
            TargetType.Meta.select_related = {item: item for item in base_sr}

        # SCHEMA INHERITANCE LOOP
        # a model mixin can pass information to its child models' schemas by specifying a TypeMeta class
        # if TypeMeta.mixin exists, then the whole class will be used as a parent for the child schema
        bases = inspect.getmro(TargetType.Meta.model)
        for BaseClass in bases:  # loop through parent classes of the TargetType we're @registering

            TypeMeta = getattr(BaseClass, 'TypeMeta', None)

            if TypeMeta:
                mixins = getattr(BaseClass.TypeMeta, 'mixins', None)

                # Mixin class will be inherited as a whole and its Meta is merged with the TargetType.Meta
                if mixins:
                    for mixin in mixins:
                        MixinClass = locate(mixin) if type(mixin) == str else mixin
                        if not MixinClass:
                            raise TypeError(f"Could not locate class {mixin} from TypeMeta.mixins of {BaseClass}")
                        if hasattr(MixinClass, 'Meta'):
                            TargetType.update_meta(**self.merged_meta_data(TargetType.Meta, MixinClass.Meta, typename))
                        TargetType = inherit_from(TargetType, MixinClass, persist_meta=False)

                select_related = getattr(TypeMeta, 'select_related', [])
                prefetch_related = getattr(TypeMeta, 'prefetch_related', [])
                extra_fields = getattr(TypeMeta, 'extra_fields', [])
                filters = getattr(TypeMeta, 'filters', {})

                if select_related:
                    TargetType.add_to_meta('select_related', select_related)

                if prefetch_related:
                    TargetType.add_to_meta('prefetch_related', prefetch_related)

                if extra_fields:
                    TargetType.add_to_meta('extra_fields', extra_fields)

                if filters:
                    meta_filters = getattr(TargetType.Meta, 'filters', dict())
                    meta_filters.update(filters)
                    TargetType.Meta.filters = meta_filters

        extra_fields = getattr(TargetType.Meta, 'extra_fields', [])

        for field, FieldType in extra_fields:
            TargetType.add_field(field, FieldType(), getattr_resolver_factory)

        self.add_node(TargetType, typename)

        return TargetType
