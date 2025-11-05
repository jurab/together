Example query

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

Registering a Django model as a schema:
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

    @property
    def description(self):
        return self.get_field_description()

        
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
