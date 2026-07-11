from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from src.auth.dependencies import (
    get_current_user,
    get_token_service,
    get_user_service,
)
from src.exceptions import ConflictError, NotFoundError
from src.auth.model import User
from src.auth.schema import RefreshRequest, TokenPair, UserCreate, UserRead
from src.auth.service import TokenAlreadyUsedError, TokenService, UserService
from src.auth.utils import REFRESH_TOKEN_TYPE, decode_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=201)
async def register_user(payload: UserCreate, service: UserService = Depends(get_user_service)):
    user = await service.create(payload)
    if not user:
        raise ConflictError(f"User with email {payload.email} already exists")
    return user


@router.post("/login", response_model=TokenPair)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    user_service: UserService = Depends(get_user_service),
    token_service: TokenService = Depends(get_token_service),
):
    """Exchange credentials for an access + refresh token pair.

    Uses OAuth2's standard password form, so the `username` field carries the
    user's email. This is also what powers Swagger UI's "Authorize" dialog.
    """
    user = await user_service.authenticate(form_data.username, form_data.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token, refresh_token = await token_service.issue_pair(user)
    return TokenPair(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenPair)
async def refresh_tokens(
    payload: RefreshRequest,
    user_service: UserService = Depends(get_user_service),
    token_service: TokenService = Depends(get_token_service),
):
    """Trade a valid refresh token for a fresh pair (the old refresh token dies)."""
    claims = _decode_refresh(payload.refresh_token)

    user = await user_service.get_by_id(UUID(claims["sub"]))
    if user is None or not user.is_active:
        raise _invalid_refresh()

    try:
        access_token, refresh_token = await token_service.rotate(UUID(claims["jti"]), user)
    except TokenAlreadyUsedError:
        raise _invalid_refresh()

    return TokenPair(access_token=access_token, refresh_token=refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    payload: RefreshRequest,
    token_service: TokenService = Depends(get_token_service),
):
    """Revoke a refresh token so it can no longer mint new access tokens.

    Access tokens already issued stay valid until they expire (they're stateless) —
    that's the tradeoff for short-lived access tokens; keep their lifetime small.
    """
    try:
        claims = _decode_refresh(payload.refresh_token)
    except HTTPException:
        # Logout is idempotent: a bad/expired token is already "logged out".
        return
    await token_service.revoke(UUID(claims["jti"]))


@router.get("/me", response_model=UserRead)
async def read_me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user — the canonical 'is my token valid' check."""
    return current_user


@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: UUID,
    service: UserService = Depends(get_user_service),
    _: User = Depends(get_current_user),
):
    user = await service.get_by_id(user_id)
    if not user:
        raise NotFoundError(f"User {user_id} not found")
    return user


def _invalid_refresh() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _decode_refresh(token: str) -> dict:
    try:
        claims = decode_token(token)
    except jwt.PyJWTError:
        raise _invalid_refresh()
    if claims.get("type") != REFRESH_TOKEN_TYPE or "jti" not in claims or "sub" not in claims:
        raise _invalid_refresh()
    return claims
