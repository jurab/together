
import channels
import channels_graphql_ws
import graphene

from api.fields import NestedField, ReverseField, ModelField
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


class OnNewChatMessage(channels_graphql_ws.Subscription):
    """Subscription triggers on a new chat message."""

    sender = ModelField(User)
    chat = ModelField(Chat)
    text = graphene.String()

    class Arguments:
        """Subscription arguments."""

        chat_id = graphene.ID()

    def subscribe(self, info, chat_id=None):
        """Client subscription handler."""
        del info
        # Specify the subscription group client subscribes to.
        return [chat_id] if chat_id is not None else None

    def publish(self, info, chat=None):
        """Called to prepare the subscription notification message."""

        assert self.chat.id == chat

        # The `self` contains payload delivered from the `broadcast()`.
        chat = Chat.objects.get(id=self["chat"])
        text = self["text"]
        sender = User.objects.get(id=self["sender"])

        # Avoid self-notifications.
        # if (info.context.user.is_authenticated and sender == info.context.user.username):
        #     return OnNewChatMessage.SKIP

        return OnNewChatMessage(chat=chat, text=text, sender=sender)

    @classmethod
    def new_chat_message(cls, chat, text, sender):
        """Auxiliary function to send subscription notifications.
        It is generally a good idea to encapsulate broadcast invocation
        inside auxiliary class methods inside the subscription class.
        That allows to consider a structure of the `payload` as an
        implementation details.
        """
        print('>>> BROADCAST')
        cls.broadcast(
            group=chat.name,
            payload={"chatroom": chat.name, "text": text, "sender": sender.username},
        )
        print('>>> DONE')


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

        # Notify subscribers.
        OnNewChatMessage.new_chat_message(chat=chat, text=text, sender=sender)

        return cls(message=message)


class Subscription(graphene.ObjectType):
    """Root GraphQL subscription."""
    new_chat_message = OnNewChatMessage.Field()
