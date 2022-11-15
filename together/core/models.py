

from django.conf import settings
from django.contrib.postgres.fields import CICharField
from django.db import models
from django.utils import timezone
from django.utils.safestring import mark_safe

from graphene.types.datetime import DateTime

from versatileimagefield.fields import VersatileImageField
from versatileimagefield.image_warmer import VersatileImageFieldWarmer


class TimestampModel(models.Model):
    """An abstract base class model providing self-updating created and modified fields."""

    created = models.DateTimeField(default=timezone.now)
    modified = models.DateTimeField(default=timezone.now)

    class Meta:
        abstract = True

    class TypeMeta:
        extra_fields = (
            ('created', DateTime),
            ('modified', DateTime),
        )


class DisplayableModelMixin:
    displayable_field = 'image'

    @property
    def thumbnail_small(self):
        return self.thumbnail(100)

    @property
    def thumbnail_large(self):
        return self.thumbnail(300)

    def thumbnail(self, max_width=200):
        image = getattr(self, self.displayable_field)

        try:
            width, height = image.width, image.height
            ratio, width = width / height, min(width, max_width)
            height = width / ratio
            return mark_safe(f'<img id="preview" src={image.url} width="{width}" height={height} />')
        except AttributeError:
            return mark_safe(f'<img id="preview" src={image.url} width="{max_width}"/>')


class Icon(models.Model, DisplayableModelMixin):
    name = CICharField(max_length=128, unique=True, help_text='Name for internal use.')
    image = models.FileField(upload_to='icons', null=False, blank=False)

    class Meta:
        ordering = 'name',

    def __str__(self):
        return self.name


class Image(models.Model, DisplayableModelMixin):
    name = CICharField(max_length=128, unique=True, help_text='Name for internal use.')
    image = VersatileImageField(upload_to='images', null=False, blank=False)

    class Meta:
        ordering = 'name',

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.image:
            try:
                # Prepare the sized versions of the image
                image_warmer = VersatileImageFieldWarmer(
                    instance_or_queryset=self,
                    rendition_key_set='default',
                    image_attr='image',
                    verbose=False  # False means no print from the versatileimagefield lib
                )
                image_warmer.warm()
            except FileNotFoundError:
                pass  # when running locally (or file gets deleted in S3, which "never happens")

    def rendition(self, key, rendition_set='default'):
        """
        Return a sized rendition of the image.

        A rendition is defined in settings with a string "key__size" (i.e. "crop__400x400")
        This method gets the key and size of a rendition from a specific set and returns
        an image object. Calling `image._rendition('crop')` with a rendition_set that includes
        ('crop', 'crop__400x400') is equivalent to calling `image.image.crop['400x400']`
        """
        if self.image:
            rendition, size = dict(settings.VERSATILEIMAGEFIELD_RENDITION_KEY_SETS[rendition_set])[key].split('__')
            return getattr(self.image, rendition)[size]


class S3Object(models.Model):

    s3url = models.CharField(max_length=1023)

    class Meta:
        abstract = True
