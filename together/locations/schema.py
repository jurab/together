
import graphene

from api.fields import NestedField
from api.filters import DjangoFilter, PaginationFilter, IDFilter
from api.registry import register_type

from .models import Location


@register_type('Location')
class LocationType:
    class Meta:
        model = Location
        queryset = Location.objects.all()
        fields = ('id created modified name description parent category'.split())
        displayable_fields = 'image', 'icon'
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
            NestedField('locations', 'self'),
            NestedField('parent', 'self'),
        }
