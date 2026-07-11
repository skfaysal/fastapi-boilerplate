from typing import Optional

from pydantic import Field, field_validator

from src.schemas import BaseSchema


class BookCreate(BaseSchema):
    title: str = Field(..., min_length=1, max_length=200)
    author: str = Field(..., min_length=1, max_length=100)
    year: int = Field(..., ge=1000, le=2100)
    price: float = Field(..., gt=0)

    @field_validator("title", "author")
    @classmethod
    def collapse_inner_whitespace(cls, v: str) -> str:
        """Normalize runs of internal whitespace: 'Clean   Code' -> 'Clean Code'.

        A `field_validator` applied to several fields at once — runs after the base
        model has already stripped the outer whitespace.
        """
        return " ".join(v.split())


class BookUpdate(BaseSchema):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    author: Optional[str] = Field(None, min_length=1, max_length=100)
    year: Optional[int] = Field(None, ge=1000, le=2100)
    price: Optional[float] = Field(None, gt=0)
