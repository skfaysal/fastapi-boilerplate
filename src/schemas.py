from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class BaseSchema(BaseModel):
    """Project-wide base for every request/response model.

    Centralizes serialization rules so every schema behaves the same way instead
    of repeating `model_config` on each class:
    - `from_attributes` — a response model can be built straight from an ORM object.
    - `str_strip_whitespace` — leading/trailing whitespace is trimmed on every str field.
    """

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class ErrorDetail(BaseSchema):
    code: str                       # machine-readable, e.g. "not_found"
    message: str                    # human-readable
    request_id: str | None = None   # ties the error back to a log line (see middleware)


class ErrorResponse(BaseSchema):
    """The single shape every error in this API comes back as: {"error": {...}}."""

    error: ErrorDetail


class Page(BaseSchema, Generic[T]):
    """A consistent envelope for every paginated list response."""

    items: list[T]
    total: int
    limit: int
    offset: int
