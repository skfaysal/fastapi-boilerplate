from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlmodel import SQLModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    username: str = Field(..., min_length=3, max_length=50, unique=True, index=True)
    email: str = Field(..., max_length=255, unique=True, index=True)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    hashed_password: str
    is_active: bool = Field(default=True)
    is_admin: bool = Field(default=False)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class RefreshToken(SQLModel, table=True):
    """Server-side record of an issued refresh token.

    The token's `jti` is stored here (as the primary key) rather than the token
    string itself — that's all we need to look one up and revoke it. Keeping this
    row lets us support logout, rotation, and reuse detection: things a purely
    stateless JWT cannot do on its own.
    """

    __tablename__ = "refresh_token"

    id: UUID = Field(primary_key=True)  # the token's jti
    user_id: UUID = Field(foreign_key="user.id", index=True)
    expires_at: datetime
    revoked: bool = Field(default=False)
    created_at: datetime = Field(default_factory=utcnow)
