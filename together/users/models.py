
from django.contrib.auth.models import AbstractUser
from django.db import models
from core.models import TimestampModel


class User(AbstractUser, TimestampModel):
    pass
