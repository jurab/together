
from django.contrib.auth.models import AbstractUser
from django.db import models


ROLES = (
    ('chef', 'Chef'),
    ('pupil', 'Pupil'),
)


class User(AbstractUser):
    role = models.CharField(choices=ROLES, max_length=16)
