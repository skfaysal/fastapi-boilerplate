from datetime import datetime, timezone
from sqlmodel import SQLModel, Field
from uuid import UUID, uuid4


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Book(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    title: str = Field(..., min_length=1, max_length=200)
    author: str = Field(..., min_length=1, max_length=100)
    year: int
    price: float
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
