
import graphene

from .models import User
from api.registry import register_type


@register_type('User')
class UserType:
    class Meta:
        model = User
        fields = ['id']
        lookups = {
            'id': graphene.ID(),
        }
