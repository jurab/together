

from django.db import models

from core.models import TimestampModel
from utils.django import names_enum
from users.models import User


class Chat(TimestampModel):
    name = models.CharField(max_length=256)
    members = models.ManyToManyField(User, through='ChatMembership', related_name='chats')

    def __str__(self):
        return self.name


ROLES = names_enum(
    'admin',
    'member',
)


class Role(models.Model):
    name = models.CharField(max_length=256, choices=ROLES)


class ChatMembership(TimestampModel):
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name='chat_memberships')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_memberships')
    role = models.CharField(max_length=256, choices=ROLES)


class Message(TimestampModel):
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name='messages')
    author = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name='messages')

    text = models.TextField()
