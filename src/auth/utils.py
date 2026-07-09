from datetime import datetime, timezone
from uuid import UUID

import bcrypt
import jwt

from src.config import Config

ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"


def hash_password(plain_password: str) -> str:
    password_bytes = plain_password.encode("utf-8")
    hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    password_bytes = plain_password.encode("utf-8")
    hashed_bytes = hashed_password.encode("utf-8")
    return bcrypt.checkpw(password_bytes, hashed_bytes)


def encode_token(*, subject: UUID, token_type: str, jti: UUID, expires_at: datetime) -> str:
    """Sign a JWT for the given subject (user id).

    Every token carries a `type` (access/refresh) so an access token can never be
    used where a refresh token is expected (or vice-versa), and a `jti` (unique id)
    so refresh tokens can be tracked and revoked server-side.
    """
    payload = {
        "sub": str(subject),
        "type": token_type,
        "jti": str(jti),
        "iat": datetime.now(timezone.utc),
        "exp": expires_at,
    }
    return jwt.encode(payload, Config.JWT_SECRET_KEY, algorithm=Config.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Verify a JWT's signature and expiry and return its claims.

    Raises `jwt.PyJWTError` (or a subclass such as `ExpiredSignatureError`) if the
    token is malformed, tampered with, or expired.
    """
    return jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=[Config.JWT_ALGORITHM])
