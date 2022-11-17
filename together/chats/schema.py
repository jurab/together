
import graphene

from api.fields import NestedField, ReverseField
from api.filters import DjangoFilter, PaginationFilter, IDFilter
from api.registry import register_type

from .models import Chat, Message
from users.schema import UserType


@register_type('Chat')
class ChatType:
    class Meta:
        model = Chat
        queryset = Chat.objects.all()
        fields = ('id created modified members'.split())
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
        }


@register_type('Message')
class MessageType:
    class Meta:
        model = Message
        queryset = Message.objects.all()
        fields = ('id created modified author text'.split())
        lookups = (
            ('id', graphene.ID()),
            ('author__name', graphene.String()),
        )
        filters = {
            'django_filter': DjangoFilter,
            'pagination': PaginationFilter,
            'ids': IDFilter
        }
        related_fields = {
            NestedField('author', UserType),
            ReverseField(ChatType, 'messages'),
        }
