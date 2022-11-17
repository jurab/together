
import graphene

from api.filters import DjangoFilter, PaginationFilter, IDFilter
from api.registry import register_type

from .models import User


@register_type('User')
class UserType:
    class Meta:
        model = User
        queryset = User.objects.all()
        fields = ('id created modified username'.split())
        lookups = (
            ('id', graphene.ID()),
            ('username', graphene.String()),
        )
        filters = {
            'django_filter': DjangoFilter,
            'pagination': PaginationFilter,
            'ids': IDFilter
        }
