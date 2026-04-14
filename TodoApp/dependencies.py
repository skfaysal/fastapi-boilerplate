"""
Central dependency registry.
All Depends() wiring lives here so routers stay thin and tests can override
a single get_db / get_current_user without touching individual files.
"""
from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session
from starlette import status

from .core.errors import ForbiddenError
from .core.security import decode_access_token
from .database import SessionLocal
from .repositories.interfaces import AbstractTodoRepository, AbstractUserRepository
from .repositories.todo_repository import TodoRepository
from .repositories.user_repository import UserRepository
from .services.auth_service import AuthService
from .services.todo_service import TodoService
from .services.user_service import UserService

oauth2_bearer = OAuth2PasswordBearer(tokenUrl="/auth/token")


# ── Database ──────────────────────────────────────────────────────────────────

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


DbDep = Annotated[Session, Depends(get_db)]


# ── Auth ──────────────────────────────────────────────────────────────────────

def get_current_user(token: Annotated[str, Depends(oauth2_bearer)]) -> dict:
    try:
        payload = decode_access_token(token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    username: str | None = payload.get("sub")
    user_id: int | None = payload.get("id")
    user_role: str | None = payload.get("role")
    if username is None or user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"username": username, "id": user_id, "user_role": user_role}


CurrentUserDep = Annotated[dict, Depends(get_current_user)]


def require_admin(user: CurrentUserDep) -> None:
    """Router-level dependency — raises 403 if the caller is not an admin."""
    if user.get("user_role") != "admin":
        raise ForbiddenError("Admin role required.")


# ── Repositories ──────────────────────────────────────────────────────────────

def get_user_repository(db: DbDep) -> AbstractUserRepository:
    return UserRepository(db)


def get_todo_repository(db: DbDep) -> AbstractTodoRepository:
    return TodoRepository(db)


# The return types are the abstract interfaces — not the concrete SQLAlchemy classes.
# Swap the database by changing only the return value of these two functions.
UserRepoDep = Annotated[AbstractUserRepository, Depends(get_user_repository)]
TodoRepoDep = Annotated[AbstractTodoRepository, Depends(get_todo_repository)]


# ── Services ──────────────────────────────────────────────────────────────────

def get_auth_service(repo: UserRepoDep) -> AuthService:
    return AuthService(repo)


def get_todo_service(repo: TodoRepoDep) -> TodoService:
    return TodoService(repo)


def get_user_service(repo: UserRepoDep) -> UserService:
    return UserService(repo)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
TodoServiceDep = Annotated[TodoService, Depends(get_todo_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
