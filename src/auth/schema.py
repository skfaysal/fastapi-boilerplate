from datetime import datetime
from uuid import UUID

from pydantic import EmailStr, Field, field_validator, model_validator

from src.schemas import BaseSchema


class UserCreate(BaseSchema):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=8, max_length=72)

    @field_validator("username", "email")
    @classmethod
    def normalize_case(cls, v: str) -> str:
        """Store usernames/emails lowercased so lookups are case-insensitive."""
        return v.lower()

    @model_validator(mode="after")
    def password_must_not_contain_username(self):
        """A cross-field rule — needs several fields at once, so it's a model_validator."""
        if self.username in self.password.lower():
            raise ValueError("password must not contain the username")
        return self


class UserRead(BaseSchema):
    id: UUID
    username: str
    email: str
    first_name: str
    last_name: str
    is_active: bool
    is_admin: bool
    created_at: datetime
    updated_at: datetime


class TokenPair(BaseSchema):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseSchema):
    refresh_token: str
