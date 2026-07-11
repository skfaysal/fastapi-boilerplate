import logging

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("app")


class AppException(Exception):
    """Base for domain errors the API knows how to turn into a response.

    Services and routers raise these (e.g. `NotFoundError`) instead of building an
    `HTTPException` by hand, so every error leaves the app through one handler in
    one consistent JSON shape.
    """

    status_code = 500
    code = "internal_error"
    message = "Something went wrong"

    def __init__(self, message: str | None = None):
        if message:
            self.message = message
        super().__init__(self.message)


class NotFoundError(AppException):
    status_code = 404
    code = "not_found"
    message = "Resource not found"


class ConflictError(AppException):
    status_code = 409
    code = "conflict"
    message = "Resource already exists"


class ForbiddenError(AppException):
    status_code = 403
    code = "forbidden"
    message = "Not allowed"


def _body(code: str, message: str, request_id: str | None, **extra) -> dict:
    return {"error": {"code": code, "message": message, "request_id": request_id, **extra}}


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def register_exception_handlers(app: FastAPI) -> None:
    """Wire every error type to the same `{"error": {...}}` response shape."""

    @app.exception_handler(AppException)
    async def _handle_app_exception(request: Request, exc: AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content=_body(exc.code, exc.message, _request_id(request)),
        )

    @app.exception_handler(RequestValidationError)
    async def _handle_validation(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content=_body(
                "validation_error",
                "Request validation failed",
                _request_id(request),
                detail=jsonable_encoder(exc.errors()),
            ),
        )

    @app.exception_handler(RateLimitExceeded)
    async def _handle_rate_limit(request: Request, exc: RateLimitExceeded):
        return JSONResponse(
            status_code=429,
            content=_body("rate_limited", "Too many requests, slow down", _request_id(request)),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _handle_http(request: Request, exc: StarletteHTTPException):
        # Covers auth's 401s etc. Preserve headers like WWW-Authenticate.
        return JSONResponse(
            status_code=exc.status_code,
            content=_body("http_error", str(exc.detail), _request_id(request)),
            headers=getattr(exc, "headers", None),
        )
