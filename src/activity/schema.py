from datetime import datetime

from pydantic import Field

from src.schemas import BaseSchema


class ActivityEvent(BaseSchema):
    """One logged event. `detail` is free-form on purpose — different event types
    carry different payloads, which is exactly why this lives in Mongo, not a table.
    """

    type: str                                   # e.g. "login", "login_failed", "book_created"
    user_id: str | None = None
    detail: dict = Field(default_factory=dict)
    ts: datetime
