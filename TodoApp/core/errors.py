"""
RFC 7807 Problem Details error handling.
https://datatracker.ietf.org/doc/html/rfc7807
"""
import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette import status
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

_STATUS_TITLES: dict[int, str] = {
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    405: "Method Not Allowed",
    409: "Conflict",
    422: "Unprocessable Entity",
    429: "Too Many Requests",
    500: "Internal Server Error",
}


# ── Domain exceptions ─────────────────────────────────────────────────────────

class AppError(Exception):
    """Base class for all application-level errors."""

    def __init__(self, status_code: int, title: str, detail: str) -> None:
        self.status_code = status_code
        self.title = title
        self.detail = detail
        super().__init__(detail)


class NotFoundError(AppError):
    def __init__(self, detail: str) -> None:
        super().__init__(status.HTTP_404_NOT_FOUND, "Not Found", detail)


class UnauthorizedError(AppError):
    def __init__(self, detail: str = "Authentication required.") -> None:
        super().__init__(status.HTTP_401_UNAUTHORIZED, "Unauthorized", detail)


class ForbiddenError(AppError):
    def __init__(self, detail: str = "Insufficient permissions.") -> None:
        super().__init__(status.HTTP_403_FORBIDDEN, "Forbidden", detail)


class ConflictError(AppError):
    def __init__(self, detail: str) -> None:
        super().__init__(status.HTTP_409_CONFLICT, "Conflict", detail)


# ── Response builder ──────────────────────────────────────────────────────────

def _problem(
    request: Request,
    status_code: int,
    title: str,
    detail: str,
    extra: dict[str, Any] | None = None,
) -> JSONResponse:
    body: dict[str, Any] = {
        "type": "about:blank",
        "title": title,
        "status": status_code,
        "detail": detail,
        "instance": request.url.path,
    }
    if extra:
        body.update(extra)
    return JSONResponse(
        status_code=status_code,
        content=body,
        media_type="application/problem+json",
    )


# ── Handler registration ──────────────────────────────────────────────────────

def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(request: Request, exc: AppError) -> JSONResponse:
        logger.warning("AppError [%s]: %s", exc.status_code, exc.detail)
        return _problem(request, exc.status_code, exc.title, exc.detail)

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        title = _STATUS_TITLES.get(exc.status_code, "Error")
        return _problem(request, exc.status_code, title, str(exc.detail))

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [
            {"field": ".".join(str(loc) for loc in e["loc"]), "message": e["msg"]}
            for e in exc.errors()
        ]
        return _problem(
            request,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Validation Error",
            "One or more fields failed validation.",
            {"errors": errors},
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
        return _problem(
            request,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Internal Server Error",
            "An unexpected error occurred.",
        )
