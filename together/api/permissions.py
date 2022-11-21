

from .exceptions import PermissionDenied


class IsAuthenticated:
    def check(info, obj=None):
        if not info.context.user.is_authenticated:
            raise PermissionDenied("You do not have permission to perform this action")
