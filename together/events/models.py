

from django.db import models

from core.models import Image, TimestampModel
from organisations.models import Organisation


class Event(TimestampModel):
    title = models.CharField(max_length=256)
    description = models.TextField(null=True)
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='events')

    image = models.ForeignKey(Image, null=True, on_delete=models.SET_NULL, related_name='events')

    def __str__(self):
        return self.name
