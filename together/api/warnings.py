

class ApiWarning:
    message = "A warning has been raised."

    def __init__(self, message):
        self.message = message

    def warn(self):
        warn(self.message)

    def location(self):
        """Return the location of resolver in the response, same as the graphQL errors."""
        return # TODO

    def as_graphql_dict(self):
        return {
            'message': self.message,
        }


def warn(warning):
    """Add a warning to the graphql response's info without interrupting the resolving."""

    if not (isinstance(warning, ApiWarning) or isinstance(warning, str)):
        raise TypeError("Warning has to be of type string or api.exceptions.ApiWarning")

    from api.meta import meta_base

    if isinstance(warning, str):
        warning = ApiWarning(warning)

    meta_base.add_warning(warning)


def get_warnings():
    """Return all pending warnings that will be return in graphql response info."""
    from api.meta import meta_base

    return meta_base.get_warnings()
