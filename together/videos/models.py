

from django.db import models

from core.models import Image, TimestampModel
from organisations.models import Organisation
from users.models import User


class Video(TimestampModel):
    name = models.CharField(max_length=256)
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='videos')

    url = models.CharField(max_length=1024)
    thumbnail = models.ForeignKey(Image, null=True, blank=True, on_delete=models.SET_NULL, related_name='video_thumbnails')

    def __str__(self):
        return self.name


class Highlight(models.Model):
    video = models.ForeignKey(Video, on_delete=models.CASCADE)

    title = models.CharField(max_length=256)
    actors = models.ManyToManyField(User, related_name='highlights', help_text='People appearing in the video.')
    start = models.BigIntegerField(help_text='Start timestamp in ms.')
    end = models.BigIntegerField(help_text='Start timestamp in ms.')
