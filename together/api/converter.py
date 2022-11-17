
import graphene
from functools import singledispatch

from django.contrib.postgres.fields import CICharField, HStoreField
from django.db import models
from django.db.models.fields import reverse_related

from api.types import IDListInput


@singledispatch
def convert_django_field_to_input(field, registry=None):
    raise Exception(
        f"Don't know how to convert the Django field into a mutation input {field} ({field.__class__})"
    )


@convert_django_field_to_input.register(models.CharField)
@convert_django_field_to_input.register(models.TextField)
@convert_django_field_to_input.register(models.EmailField)
@convert_django_field_to_input.register(CICharField)
def convert_field_to_string(field, registry=None):
    required = not (field.blank or field.default is not None)
    return graphene.String(description=field.help_text, required=required)


@convert_django_field_to_input.register(models.PositiveIntegerField)
@convert_django_field_to_input.register(models.PositiveSmallIntegerField)
@convert_django_field_to_input.register(models.SmallIntegerField)
@convert_django_field_to_input.register(models.BigIntegerField)
@convert_django_field_to_input.register(models.IntegerField)
def convert_field_to_int(field, registry=None):
    required = not (field.blank or field.default is not None)
    return graphene.Int(description=field.help_text, required=required)


@convert_django_field_to_input.register(models.NullBooleanField)
@convert_django_field_to_input.register(models.BooleanField)
def convert_field_to_boolean(field, registry=None):
    required = not (field.blank or field.default is not None)
    return graphene.Boolean(description=field.help_text, required=required)


@convert_django_field_to_input.register(models.DecimalField)
@convert_django_field_to_input.register(models.FloatField)
def convert_field_to_float(field, registry=None):
    required = not (field.blank or field.default is not None)
    return graphene.Float(description=field.help_text, required=required)


@convert_django_field_to_input.register(models.DateTimeField)
def convert_datetime_to_string(field, registry=None):
    required = not (field.blank or field.default is not None)
    return graphene.DateTime(description=field.help_text, required=required)


@convert_django_field_to_input.register(models.DateField)
def convert_date_to_string(field, registry=None):
    required = not (field.blank or field.default is not None)
    return graphene.Date(description=field.help_text, required=required)


@convert_django_field_to_input.register(models.TimeField)
def convert_time_to_string(field, registry=None):
    required = not (field.blank or field.default is not None)
    return graphene.Time(description=field.help_text, required=required)


@convert_django_field_to_input.register(models.ForeignKey)
@convert_django_field_to_input.register(models.OneToOneField)
@convert_django_field_to_input.register(models.AutoField)
def convert_related_key_to_id(field, registry=None):
    required = not (field.blank or field.default is not None)
    return graphene.ID(description=field.help_text, required=required)


@convert_django_field_to_input.register(models.ManyToManyField)
def convert_m2m_to_list(field, registry=None):
    required = not (field.blank or field.default is not None)
    return IDListInput(description=field.help_text, required=required)


@convert_django_field_to_input.register(HStoreField)
def convert_hstore_to_json(field, registry=None):
    required = not (field.blank or field.default is not None)
    return graphene.JSONString(description=field.help_text, required=required)


@convert_django_field_to_input.register(reverse_related.ManyToOneRel)
@convert_django_field_to_input.register(reverse_related.ManyToManyRel)
def convert_reverse_many_to_list(rel, registry=None):
    return IDListInput(description=rel.field.help_text, required=False)


@convert_django_field_to_input.register(reverse_related.OneToOneRel)
@convert_django_field_to_input.register(reverse_related.ForeignObjectRel)
def convert_reverse_related_key_to_list(rel, registry=None):
    return graphene.ID(description=rel.field.help_text, required=False)

@convert_django_field_to_input.register(models.UUIDField)
def convert_uuid_to_uuid(field, registry=None):
    return graphene.UUID(description=field.help_text, required=False)
