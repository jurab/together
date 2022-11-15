

from django.db import models

from core.models import TimestampModel
from organisations.models import Organisation
from users.models import User


class Request(TimestampModel):
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='memberships')
    text = models.TextField()
