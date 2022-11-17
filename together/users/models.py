
from django.contrib.auth.models import AbstractUser
from django.db import models
from core.models import TimestampModel


ROLES = (
    ('chef', 'Chef'),
    ('pupil', 'Pupil'),
)


class User(AbstractUser, TimestampModel):
    role = models.CharField(choices=ROLES, max_length=16)
