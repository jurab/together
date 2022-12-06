

from django.db import models

from core.models import Image, TimestampModel
from organisations.models import Organisation
from utils.django import names_enum
from users.models import User


CATEGORIES = names_enum(
    'job',
    'news',
)


class Post(TimestampModel):
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, help_text='Can be null if the author-user had been deleted.')
    title = models.CharField(max_length=256)
    description = models.TextField(null=True)
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='posts')

    image = models.ForeignKey(Image, null=True, on_delete=models.SET_NULL, related_name='posts')
    gallery = models.ManyToManyField(Image, related_name='post_galleries')

    def __str__(self):
        return self.title
