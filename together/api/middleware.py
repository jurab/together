
from .meta import QueryMeta, reset_meta, meta_base
from .parsing import get_operation_name
from .utils import is_root_info


class MetaFieldResolverMiddleware:
    """
    Meta middleware

    Graphene style middlware - gets called on resolving each field in the response.
    Checks whether there are more operations than one and if yes, activates the correct Meta
    for each field.
    """

    def resolve(self, next, root, info, *args, **kwargs):

        operation_name = get_operation_name(info)

        if is_root_info(info) and 'meta' in kwargs:
            meta = QueryMeta(kwargs['meta'])
            meta_base.add_meta(operation_name, meta)

        try:
            meta_base.activate_query(operation_name)
        except KeyError:
            meta_base.activate_query('default')

        return next(root, info, *args, **kwargs)


class TimeoutMiddleware:
    """
    Timeout middleware

    Checks the MetaBase timer and raises an error if the request is taking too long, aborting the whole operation.
    """

    def resolve(self, next, root, info, *args, **kwargs):
        meta_base.abort_request_if_timedout()
        return next(root, info, *args, **kwargs)


class MetaCleanupMiddleware:
    """Resets BaseMeta when request is fullfiled."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        reset_meta()
        response = self.get_response(request)
        reset_meta()
        return response
