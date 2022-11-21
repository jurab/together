
import graphene

from api.fields import NestedField, ReverseField
from api.filters import DjangoFilter, PaginationFilter, IDFilter
from api.mutations import Save
from api.registry import register_type, register_mutation

from .models import Chat, Message
from users.models import User
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
        fields = ('id created modified text'.split())
        lookups = (
            ('id', graphene.ID()),
        )
        filters = {
            'django_filter': DjangoFilter,
            'pagination': PaginationFilter,
            'ids': IDFilter
        }
        related_fields = {
            NestedField('sender', UserType),
            ReverseField(ChatType, 'messages'),
        }


@register_mutation
class SendChatMessage(Save):
    class Meta:
        model = Message
        exclude_arguments = 'id created modified'.split()

    @classmethod
    def mutate(cls, root, info, chat, sender, text):
        """Mutation "resolver" - store and broadcast a message."""

        chat = Chat.objects.get(id=chat)
        sender = User.objects.get(id=sender)
        message = Message.objects.create(chat=chat, sender=sender, text=text)

        return cls(message=message)
