

from django.db import models

from core.models import Image, Icon, TimestampModel
from locations.models import Location
from utils.django import names_enum
from users.models import User


CATEGORIES = names_enum(
    'church',
    'job',
    'music',
    'news',
    'non-profit',
    'public service',
    'school',
    'sports',
    'volunteering'
)


class Organisation(TimestampModel):
    name = models.CharField(max_length=256, unique=True, blank=True)
    members = models.ManyToManyField(User, through='Membership', related_name='admined_organisations')

    category = models.CharField(max_length=32, choices=CATEGORIES)

    location = models.ForeignKey(Location, on_delete=models.PROTECT, related_name='organisations')
    profile_image = models.ForeignKey(Image, null=True, on_delete=models.SET_NULL, related_name='organisations')
    icon = models.ForeignKey(Icon, null=True, on_delete=models.SET_NULL, related_name='organisations')

    def __str__(self):
        return self.name


ROLES = names_enum(
    'admin',
    'member',
    'following'
)


class Role(models.Model):
    name = models.CharField(max_length=256, choices=ROLES)


class Membership(TimestampModel):
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='memberships')
    role = models.CharField(max_length=256, choices=ROLES)
