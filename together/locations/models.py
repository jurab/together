

from django.db import models

from core.models import TimestampModel, Image, Icon
from utils.django import names_enum


CATEGORIES = names_enum('country', 'county', 'town', 'state')


class Location(TimestampModel):
    name = models.CharField(max_length=256)
    description = models.TextField(null=True)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='locations')
    category = models.CharField(max_length=32, choices=CATEGORIES)

    image = models.ForeignKey(Image, null=True, on_delete=models.SET_NULL, related_name='locations')
    icon = models.ForeignKey(Icon, null=True, on_delete=models.SET_NULL, related_name='locations')

    def __str__(self):
        return self.name
