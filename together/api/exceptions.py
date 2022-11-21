
from graphql import GraphQLError


class MetaConfigurationError(Exception):
    message = "Meta class improperly configured for Type."


class NodeAlreadyRegistered(Exception):
    message = "Node already registered."


class NodeNotFound(Exception):
    message = "Node not found."

    def __init__(self, message, missing_type):
        self.message = message
        self.Type = missing_type


class RelatedTypeNotFound(Exception):
    message = "Node not found."

    def __init__(self, message, model):
        self.message = message
        self.model = model


class PermissionDenied(GraphQLError):
    pass


class TimeoutExit(BaseException):
    """
    Exit the request because of a timeout.

    Using BaseException as a base class is generally an antipattern, use with caution.

    The reason we inherit from BaseException is that graphql-core relies on the
    promise library. The promise library is an ugly JavaScript port of a motherfucker.
    It allows you to lazy chain an unlimited number of methods and to swallow
    exceptions between every evaluation. It's essentially like this:

    Promise.resolve(None).then(method_1).catch(catch_1).then(method_2).catch(catch_2).then(method_3).catch(catch_3)

    ^ that is the same as:

    try:
        try:
            try:
                method_1()
            except Exception as e:
                catch_1(e)
            method_2()
        except Exception as e:
            catch_2(e)
        method_3()
    except Exception as e:
        catch_3(e)

    GraphQL's only catch handler is a "add `e` to a list and pass"
    and the handler is an inline function, so not monkey-patchable.

    That's why we make use of a BaseException. It's a super class
    of Exception, so it doesn't get caught. It's on the same level
    as exit(), so use with very high caution.
    """
    message = "The request timed out."
