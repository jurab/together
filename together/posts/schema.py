
import graphene

from api.fields import NestedField, ReverseField
from api.filters import DjangoFilter, PaginationFilter, IDFilter, enum_filter_factory
from api.registry import register_type

from .models import Post
from organisations.schema import OrganisationType
from users.schema import UserType


# class CategoryEnum(graphene.Enum):
#     JOB = 'job'
#     NEWS = 'news'
#
#     def get_field_description(self):
#         descriptions = {
#             "JOB": "Job posting.",
#             "NEWS": "News update.",
#         }
#         return descriptions.get(self.name)
#
#     @property
#     def description(self):
#         return self.get_field_description()
#
#
# class CategoryFilter:
#     input = CategoryEnum()
#
#     def apply(self, qs, category):
#         return qs.filter(category=category)


POST_CATEGORIES = {
    "JOB": "Job posting.",
    "NEWS": "News update.",
}


@register_type('Post')
class PostType:

    class Meta:
        model = Post
        queryset = Post.objects.all()
        fields = ('id created modified title description category'.split())
        displayable_fields = 'image',
        prefetch_related = 'members',
        lookups = (
            ('id', graphene.ID()),
            ('title', graphene.String()),
        )
        filters = {
            'django_filter': DjangoFilter,
            'pagination': PaginationFilter,
            'ids': IDFilter,
            'category': enum_filter_factory('PostCategory', 'category', POST_CATEGORIES),
        }
        related_fields = {
            NestedField('organisation', OrganisationType),
            NestedField('author', UserType),
            ReverseField(OrganisationType, 'posts'),
        }
