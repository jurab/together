
import json
# import sentry_sdk

from django.conf import settings
from django.http import HttpResponse

from .meta import TimeoutExit

from graphene_django.views import GraphQLView as DefaultGraphQlView


SUCCESS = dict((
    ('FULL', 'FULL'),
    ('PARTIAL', 'PARTIAL'),
    ('NONE', 'NONE'),
    ('TIMEOUT', 'TIMEOUT')
))


class GraphQLView(DefaultGraphQlView):
    """Capture original non-gql errors in sentry before returning gql response."""

    def execute_graphql_request(self, *args, **kwargs):
        result = super().execute_graphql_request(*args, **kwargs)
        # if result.errors:
        #     self._sentry_capture(result.errors)
        return result

    # def _sentry_capture(self, errors):
    #     for error in errors:
    #         sentry_sdk.capture_exception(getattr(error, 'original_error', error))

    def _add_response_field(self, response, name, value):
        try:
            data = json.loads(response.content)
            data[name] = value
            response.content = json.dumps(data)
            return response
        except json.decoder.JSONDecodeError:
            return response

    def _evaluate_success(self, response):
        if 'errors' not in response:
            return SUCCESS['FULL']
        if 'data' not in response:
            return SUCCESS['NONE']
        return SUCCESS['PARTIAL']

    def _timeout_response(self):
        return HttpResponse(content=json.dumps({
            'data': None,
            'errors': [{'message': f"The request timed out (>{settings.GRAPHQL_TIMEOUT}ms)."}]}))

    def dispatch(self, *args, **kwargs):

        try:
            result = super(GraphQLView, self).dispatch(*args, **kwargs)
            success = self._evaluate_success(result)
        except TimeoutExit:
            result = self._timeout_response()
            success = SUCCESS['TIMEOUT']

        result = self._add_response_field(result, 'success', success)
        return result
