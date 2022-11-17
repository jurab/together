
import graphene

from api.fields import NestedField, ReverseField
from api.filters import DjangoFilter, PaginationFilter, IDFilter
from api.registry import register_type

from .models import Organisation
from locations.schema import LocationType
from users.schema import UserType


@register_type('Organisation')
class OrganisationType:
    class Meta:
        model = Organisation
        queryset = Organisation.objects.all()
        fields = ('id created modified name members category location'.split())
        displayable_fields = 'profile_image', 'icon'
        lookups = (
            ('id', graphene.ID()),
            ('name', graphene.String()),
        )
        filters = {
            'django_filter': DjangoFilter,
            'pagination': PaginationFilter,
            'ids': IDFilter
        }
        related_fields = {
            NestedField('members', UserType),
            NestedField('location', LocationType),
            ReverseField(UserType, 'admined_organisations'),
            ReverseField(LocationType, 'organisations'),
        }
