# -*- coding: utf-8 -*-

# core django imports
from django.conf import settings
from django.conf.urls import url
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path
from django.views.decorators.csrf import csrf_exempt

from api.views import GraphQLView


urlpatterns = [
    # General
    url(r'^admin', admin.site.urls),

    path("graphql", csrf_exempt(GraphQLView.as_view(graphiql=True))),
    path("graphql/", csrf_exempt(GraphQLView.as_view(graphiql=True))),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)  # + app_url_patterns

admin.autodiscover()
