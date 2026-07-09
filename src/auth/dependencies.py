from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.main import get_session
from src.auth.model import User
from src.auth.service import TokenService, UserService
from src.auth.utils import ACCESS_TOKEN_TYPE, decode_token

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
    except jwt.PyJWTError:
        raise _credentials_error

    if payload.get("type") != ACCESS_TOKEN_TYPE:
        raise _credentials_error

    user_id = payload.get("sub")
    if user_id is None:
        raise _credentials_error

    user = await service.get_by_id(UUID(user_id))
    if user is None or not user.is_active:
        raise _credentials_error

    return user
