

from django.db import models

from core.models import Image, TimestampModel
from organisations.models import Organisation
from utils.django import names_enum
from users.models import User


class Event(TimestampModel):
    title = models.CharField(max_length=256)
    description = models.TextField(null=True)
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='events')

    image = models.ForeignKey(Image, null=True, on_delete=models.SET_NULL, related_name='events')
    gallery = models.ManyToManyField(Image, related_name='event_galleries')

    members = models.ManyToManyField(User, through='Attendance', related_name='events')

    def __str__(self):
        return self.title


ROLES = names_enum(
    'admin',
    'going',
    'following'
)


class Role(models.Model):
    name = models.CharField(max_length=256, choices=ROLES)


class Attendance(TimestampModel):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='attendances')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='attendances')
    role = models.CharField(max_length=256, choices=ROLES)
