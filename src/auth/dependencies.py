import logging
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.main import get_session
from src.exceptions import ForbiddenError
from src.logging_config import user_id_ctx
from src.auth.model import User
from src.auth.service import TokenService, UserService
from src.auth.utils import ACCESS_TOKEN_TYPE, decode_token

logger = logging.getLogger("app")

# tokenUrl points at the login endpoint so Swagger UI's "Authorize" button works.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

_credentials_error = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_user_service(session: AsyncSession = Depends(get_session)) -> UserService:
    return UserService(session)


def get_token_service(session: AsyncSession = Depends(get_session)) -> TokenService:
    return TokenService(session)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    service: UserService = Depends(get_user_service),
) -> User:
    """Resolve and validate the bearer access token into the current `User`.

    Rejects anything that isn't a valid, unexpired *access* token, or that points
    at a missing/inactive user. Attach this as a dependency to protect an endpoint.
    """
    try:
        payload = decode_token(token)
        if payload.get("type") != ACCESS_TOKEN_TYPE or payload.get("sub") is None:
            raise _credentials_error
        user = await service.get_by_id(UUID(payload["sub"]))
        if user is None or not user.is_active:
            raise _credentials_error
    except (jwt.PyJWTError, HTTPException):
        logger.warning("auth failed: rejected access token")
        raise _credentials_error

    user_id_ctx.set(str(user.id))          # stamp subsequent log lines with the user
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    """Authorization gate: only let admins through. Layers on top of get_current_user."""
    if not user.is_admin:
        logger.warning("forbidden: non-admin user %s attempted an admin action", user.id)
        raise ForbiddenError("Admin privileges required")
    return user
