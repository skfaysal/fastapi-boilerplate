from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from ..dependencies import AuthServiceDep
from ..schemas.auth import CreateUserRequest, Token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    responses={
        409: {"description": "Username or email already taken"},
        422: {"description": "Validation error"},
    },
)
async def create_user(data: CreateUserRequest, service: AuthServiceDep) -> None:
    service.register(data)


@router.post(
    "/token",
    response_model=Token,
    summary="Login — obtain a JWT bearer token",
    responses={
        401: {"description": "Invalid credentials"},
    },
)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    service: AuthServiceDep,
) -> Token:
    return service.login(form_data.username, form_data.password)
