"""Our own error classes and the handlers that turn them into JSON (architecture section 5).

The layers above storage never see raw sqlite3 errors, and the client never sees
stack traces, SQL, tokens or the values it sent (NFR-8).
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class StoreError(Exception):
    """Something went wrong in the storage layer."""


class StoreBusyError(StoreError):
    """The database stayed locked longer than busy_timeout (ADR-0004)."""


class StoreIntegrityError(StoreError):
    """A constraint or trigger rejected the write, for example editing the ledger."""


class AppError(Exception):
    """An error we expect, with a fixed status code and error code (docs/api.md section 2)."""

    status_code = 500
    code = "internal_error"
    message = "Something went wrong. Nothing was changed."

    def __init__(self, message: str | None = None) -> None:
        if message is not None:
            self.message = message
        super().__init__(self.message)


class InvalidToken(AppError):
    status_code = 401
    code = "invalid_token"
    message = "The access token is missing, wrong or expired."


class Forbidden(AppError):
    status_code = 403
    code = "forbidden"
    message = "You are not allowed to do this."


class NotFound(AppError):
    status_code = 404
    code = "not_found"
    message = "The requested item does not exist."


class ValidationFailed(AppError):
    status_code = 422
    code = "validation_error"
    message = "The request is not valid."


def error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": {"code": code, "message": message}})


async def handle_app_error(request: Request, error: AppError) -> JSONResponse:
    return error_response(error.status_code, error.code, error.message)


async def handle_validation_error(request: Request, error: RequestValidationError) -> JSONResponse:
    # FastAPI's default reply echoes the input back, so we send a fixed message instead.
    return error_response(422, "validation_error", ValidationFailed.message)


async def handle_http_error(request: Request, error: StarletteHTTPException) -> JSONResponse:
    if error.status_code == 404:
        return error_response(404, "not_found", NotFound.message)
    if error.status_code == 405:
        return error_response(405, "method_not_allowed", "This method is not allowed here.")
    return error_response(error.status_code, "http_error", "The request could not be handled.")


async def handle_busy_error(request: Request, error: StoreBusyError) -> JSONResponse:
    return error_response(503, "busy", "The database is busy. Please try again.")


async def handle_unexpected_error(request: Request, error: Exception) -> JSONResponse:
    return error_response(500, AppError.code, AppError.message)


def add_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, handle_app_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, handle_http_error)
    app.add_exception_handler(StoreBusyError, handle_busy_error)
    app.add_exception_handler(Exception, handle_unexpected_error)
