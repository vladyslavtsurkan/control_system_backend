__all__ = [
    "ObjectNotFoundException",
    "ObjectAlreadyExistsException",
    "GoneException",
    "NotAuthorizedException",
    "ForbiddenException",
    "BadRequestException",
]

from app.enums import MessageException


class ObjectNotFoundException(Exception):
    """
    Exception raised when an object with a specified identifier is not found in a given model.
    """

    def __init__(
        self, id_: any = None, model_name: str | None = None, message: str = MessageException.object_not_found
    ) -> None:
        self.message = message
        super().__init__(self.message)
        self.alias = {"id": id_, "model_name": model_name}


class ObjectAlreadyExistsException(Exception):
    """
    Exception raised when an object with a specified identifier is already present in a given model.
    """

    def __init__(self, id_: any, model_name: str, message: str = MessageException.object_already_exists) -> None:
        self.message = message
        super().__init__(self.message)
        self.alias = {"id": id_, "model_name": model_name}


class GoneException(Exception):
    """
    Exception raised when a resource is permanently removed.
    """

    def __init__(self, message: str = MessageException.gone) -> None:
        self.message = message
        super().__init__(self.message)
        self.alias = {}


class NotAuthorizedException(Exception):
    """
    Exception raised when a request lacks proper authorization credentials, resulting in a 401 Unauthorized response.
    """

    def __init__(self, message: str = MessageException.not_authorized) -> None:
        self.message = message
        super().__init__(self.message)
        self.alias = {}


class ForbiddenException(Exception):
    """
    Exception raised when a request lacks proper authorization credentials, resulting in a 403 Forbidden response.
    """

    def __init__(self, message: str = MessageException.forbidden) -> None:
        self.message = message
        super().__init__(self.message)
        self.alias = {}


class BadRequestException(Exception):
    """
    Exception raised when a request is malformed.
    """

    def __init__(self, message: str = MessageException.bad_request, alias: dict = None) -> None:
        self.message = message
        super().__init__(self.message)
        self.alias = alias if alias else {}
