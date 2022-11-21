
import graphene
import graphql_jwt

from api.filters import DjangoFilter, PaginationFilter, IDFilter
from api.mutations import Mutation
from api.registry import register_type, register_mutation

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


@register_mutation
class Mutation(Mutation):
    token_auth = graphql_jwt.ObtainJSONWebToken.Field()
    verify_token = graphql_jwt.Verify.Field()
    refresh_token = graphql_jwt.Refresh.Field()
