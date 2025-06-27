from fastapi import Request, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.core.exc import base as exc

__all__ = [
    "handle_object_not_found",
    "handle_object_already_exists",
    "handle_gone_exception",
    "handle_not_authorized_exception",
    "handle_forbidden_exception",
    "handle_bad_request_exception",
    "handle_validation_error",
]


def handle_object_not_found(_: Request, e: exc.ObjectNotFoundException) -> JSONResponse:
    return JSONResponse(content={"message": str(e)}, status_code=status.HTTP_404_NOT_FOUND)


def handle_object_already_exists(_: Request, e: exc.ObjectAlreadyExistsException) -> JSONResponse:
    return JSONResponse(content={"message": str(e)}, status_code=status.HTTP_409_CONFLICT)


def handle_gone_exception(_: Request, e: exc.GoneException) -> JSONResponse:
    return JSONResponse(content={"message": str(e)}, status_code=status.HTTP_410_GONE)


def handle_not_authorized_exception(_: Request, e: exc.NotAuthorizedException) -> JSONResponse:
    return JSONResponse(content={"message": str(e)}, status_code=status.HTTP_401_UNAUTHORIZED)


def handle_forbidden_exception(_: Request, e: exc.ForbiddenException) -> JSONResponse:
    return JSONResponse(content={"message": str(e)}, status_code=status.HTTP_403_FORBIDDEN)


def handle_bad_request_exception(_: Request, e: exc.BadRequestException) -> JSONResponse:
    return JSONResponse(content={"message": str(e)}, status_code=status.HTTP_400_BAD_REQUEST)


def handle_validation_error(_: Request, e: ValidationError) -> JSONResponse:
    return JSONResponse(content={"message": str(e)}, status_code=status.HTTP_400_BAD_REQUEST)
