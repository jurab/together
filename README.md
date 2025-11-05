Example query:
```graphql
organisations {
  id
  name
  events(pagination: (limit: 10, offset: 20)){
    members(
      role: GOING,
      djangoFilter: (filter: "username__startswith='A'")){
        username
    }
}
```

Registering a Django model as a graphql schema:
```python
class RoleEnum(graphene.Enum):
    ADMIN = 'admin'
    GOING = 'going'
    FOLLOWING = 'following'

    def get_field_description(self):
        descriptions = {
            "ADMIN": "Has admin privileges for this event.",
            "GOING": "Wants to attend the event.",
            "FOLLOWING": "Follows the event."
        }
        return descriptions.get(self.name)


@register_type('Event')
class EventType:

    members = ModelListField(User, role=RoleEnum())

    class Meta:
        model = Event
        queryset = Event.objects.all()
        fields = ('id created modified title description'.split())
        displayable_fields = 'image',
        prefetch_related = 'members',
        lookups = (
            ('id', graphene.ID()),
            ('title', graphene.String()),
        )
        filters = {
            'django_filter': DjangoFilter,
            'pagination': PaginationFilter,
            'ids': IDFilter
        }
        related_fields = {
            NestedField('organisation', OrganisationType),
            ReverseField(OrganisationType, 'events'),
        }

    def resolve_members(event, *args, **kwargs):
        role = kwargs.get('role', None)
        return event.members.filter(role=role)

```

---

## Internal documentation for the original project I implemented the API library for

# Setup

The PSQL DB needs to have the citext and hstore extensions:
`create extension citext;`
`create extension hstore;`


# The GraphQL api

You can easily register new schemas in the GraphQL API with the [api module](/plantjammer/api).

## Contents

- [registering queries](#queries)
- [filtering](#filtering)
- [internationalisation](#internationalisation)
- [nesting schemas](#nesting-schemas)
- [custom fields](#custom-fields)
- [registering mutations](#mutations)
- [inheritance](#inheritance)
- [docs](#docs)

## Full type meta overview


| Meta attribute     | Required        | Type                                 | Reference     |
| -------------      | -------------   | -------------                        | ------------- |
| model              | Yes             | class                                | [registering](#queries)
| fields             | Yes             | strings                              | [registering](#queries)
| lookups            | Yes             | tuples (name, graphene_type)         | [registering](#queries)
| translated_fields  |                 | strings                              | [internationalisation](#internationalisation)
| related_fields     |                 | list of NestedField or ReverseField  | [nesting schemas](#nesting-schemas)
| filters            |                 | list of filters                      | [filtering](#filtering)
| extra_fields       |                 | fields annotated by filters          | [filtering](#filtering)

# Queries

```python
from api.registry import register_type

@register_type('Tag')
class TagType:
    class Meta:
        model = Tag
        queryset = Tag.objects.all()
        fields = '__all__'
        lookups = ('id', graphene.ID()),
```

## Type class

The Type class has to be decorated by `api.registry.register_type`
   - typename is the name of the schema as you want it to appear in the API, not passing it will keep the name of decorated class

## Minimal Type Meta:
  `model`: Django model
  
  `queryset`: Django qs
  
  `fields`: iterable of field names or \_\_all__
  
  `lookups`: iterable of tuples (name: graphene_field_instance), define which attributes to use for object lookup in GraphQL and what graphene type they are

   - [all options for registration](#type-options)


# Filtering

Filtering is straightforward to implement. You need a filter class with an attribute `input` that will specify what graphene input does the filter need and an `apply` method that accepts a queryset and the filter input, and **returns a queryset**. 

```python
class IDFilter:
    input = graphene.List(graphene.ID)

    def apply(self, qs, ids):
        return qs.filter(id__in=ids)
```

```python
@register_type('Tag')
class TagType:
    class Meta:
        model = Tag
        queryset = Tag.objects.all()
        fields = '__all__'
        lookups = ('id', graphene.ID()),
        filters = {
            'ids': IDFilter
        }
```

The filters can also **annotate** the queryset with extra attributes. In order to display the annotations in the API, you have to add the names of the new attributes to the type's `Meta.extra_fields` attribute.

## API filters
Found in the [api module](/plantjammer/api/filters.py)


| Filter                            | Description |
| -------------                     | ------------- |
| IDFilter                          | Simple filter to get objects by id.  |
| PaginationFilter                  | Limits the response size |
| DjangoFilter                      | Runs Django ORM filtering on the QS |

### PaginationFilter
`limitTo`: Number of objects to return

`offset`: The number of objects to skip

### DjangoFilter
This is a direct way to tap into the ORM. The filter expression will be parsed straight into a Django lookup.
```graphql
query {
  ingredients(djangoFilter: {filter: "name__en__contains='app'"}){
    name
  }
}
```
Is the equivalent of `.objects.filter(name__en__contains='app')` 

## Core filters 
Found in the [core module](/plantjammer/core/filters.py)

| Filter                            | Description |
| -------------                     | ------------- |
| TagFilterAnd                      | Returns objets that have `ALL` the tags passed to the filter  |
| TagFilterOr                       | Returns objets that have `ANY` the tags passed to the filter |
| StringSearchFilter                | Filters objects based on a specified field. |
| MultilingualNameSearchFilter      | Searches a multilingual field based on the active language. |

- TagFilterAnd: Returns objets that have `ALL` the tags passed to the filter

- TagFilterOr: Returns objets that have `ANY` the tags passed to the filter

- StringSearchFilter: You need to initialize its `search_field` attribute.

- MultilingualNameSearchFilter: Searches a multilingual field based on the active language.


# Internationalisation
```python
@register_type('Tag')
class TagType:
    class Meta:
        model = Tag
        queryset = Tag.objects.all()
        fields = 'id',
        translated_fields = 'multilingual_name',
```

```graphql
# Translate only a specific field
query {
  tags{
    id
    name_de: multilingualName(forceField: de)
    name_es: multilingualName(forceField: es)
  }
}
```

```graphql
# Force a single field to be evaluated in Spanish
query {
  tags(meta: {language: es}){
    id
    multilingualname
  }
}
```

In order to make a field translatable, it needs to be (a) a ForeignKey/1-1 field on the Django model and (b) added to the Type's `Meta.translated_fields`.


# Nesting Schemas

Models that have relations to other models can show them as nested types in the API. You only need to register each type once.

You register relations between types using the `Meta.related_fields` attribute. It accepts `api.fields.NestedField` and `api.fields.ReverseField`.
The options differ based on the direction. In a single .py file, you can safely nest using the `api.fields.NestedField` attribute, but sometimes you want to nest a fringe type under a core one; for that purpose you should use `api.fields.ReverseField` to avoid spaghetti dependencies.

```python
from api.fields import NestedField, ReverseField

@register_type('Step')
class StepType:

    class Meta:
        model = Step
        fields = 'id', 'text'
        
@register_type('Blueprint')
class BlueprintType:

    class Meta:
        model = Blueprint
        fields = 'id',
        related_fields = {
            NestedField('steps', StepType, reverse_key='blueprint'),  # Adds a `steps` field to this schema
            ReverseField(TagType, 'blueprints'),  # Adds a `blueprints` field to the TagType schema
        }
```

In this example the `StepType` is defined in the same app as `BlueprintType`, so there is no issue with nesting the field directly. There will be a `Blueprint.steps` field now with the same setup as the `StepType`.

The TagType is from `core` and we don't want the core to have a dependency on a lower app like blueprints.

If you want to get blueprints of a tag as `Tag.blueprints`, then you need to add a `ReverseField` to the Blueprint type.


# Custom fields

Sometimes you need to add a programatic field that is not defined on the model. Graphene's original way of implementing fields still works.

```python
@register_type('Tag')
class TagType:

    extra_text = graphene.String(the_text=graphene.String, description="Some text to add to every object")

    class Meta:
        model = Tag
        queryset = Tag.objects.all()
        fields = '__all__'
        lookups = ('id', graphene.ID()),
        
    def extra_text(obj, *args, **kwargs):
        text = kwargs['the_text']
        return text
```

A more complex example can be found in the [methods.schema.InstructionsGeneratorSchemaMixin](/plantjammer/blueprints/schemas.py)


# Registering mutations

Registering mutations is simple once you registered the type.

```python
from api.registry import register_mutation

@register_mutation
class SaveTag(Save):
    class Meta:
        model = Tag
        exclude_arguments = 'owner created modified'.split()


@register_mutation
class DeleteTag(Delete):
    class Meta(Delete.Meta):
        model = Tag     
```

You can register your own kinds of mutations. An example of that is [core.schema.BulkUpdateMultilingual](/plantjammer/core/schema)

# Inheritance

Graphene and graphene-django essentialy break inheritance between schemas.

There are two ways to quickly enhance schemas. One is to use schema mixins which are quite simple, an example is the [methods.schema.InstructionsGeneratorSchemaMixin](/plantjammer/methods/schema).

The other mechanism is to tell a Django model mixin to inform its schema about some extra functionalities.


Telling the schema of any TaggableModel to inherit from the TaggableModelSchemaMixin:
```python
class TaggableModel(models.Model):

    tags = OwnedManyToManyField(Tag, blank=True)

    class Meta:
        abstract = True

    class TypeMeta:
        mixins = 'core.types.TaggableModelSchemaMixin',
```

Telling the schema of any TimestampModel to add 2 extra fields - created and modified.
```python
class TimestampModel(models.Model):
    """An abstract base class model providing self-updating created and modified fields."""

    created = models.DateTimeField(default=timezone.now)
    modified = models.DateTimeField(default=timezone.now)

    class Meta:
        abstract = True

    class TypeMeta:
        extra_fields = (
            ('created', DateTime),
            ('modified', DateTime),
        )
```
