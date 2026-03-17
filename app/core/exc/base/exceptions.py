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
        self, id_: any = None, model_name: str | None = None, message: str = MessageException.OBJECT_NOT_FOUND
    ) -> None:
        self.message = message
        super().__init__(self.message)
        self.alias = {"id": id_, "model_name": model_name}


class ObjectAlreadyExistsException(Exception):
    """
    Exception raised when an object with a specified identifier is already present in a given model.
    """

    def __init__(self, id_: any, model_name: str, message: str = MessageException.OBJECT_ALREADY_EXISTS) -> None:
        self.message = message
        super().__init__(self.message)
        self.alias = {"id": id_, "model_name": model_name}


class GoneException(Exception):
    """
    Exception raised when a resource is permanently removed.
    """

    def __init__(self, message: str = MessageException.GONE) -> None:
        self.message = message
        super().__init__(self.message)
        self.alias = {}


class NotAuthorizedException(Exception):
    """
    Exception raised when a request lacks proper authorization credentials, resulting in a 401 Unauthorized response.
    """

    def __init__(self, message: str = MessageException.NOT_AUTHORIZED) -> None:
        self.message = message
        super().__init__(self.message)
        self.alias = {}


class ForbiddenException(Exception):
    """
    Exception raised when a request lacks proper authorization credentials, resulting in a 403 Forbidden response.
    """

    def __init__(self, message: str = MessageException.FORBIDDEN) -> None:
        self.message = message
        super().__init__(self.message)
        self.alias = {}


class BadRequestException(Exception):
    """
    Exception raised when a request is malformed.
    """

    def __init__(self, message: str = MessageException.BAD_REQUEST, alias: dict = None) -> None:
        self.message = message
        super().__init__(self.message)
        self.alias = alias if alias else {}
