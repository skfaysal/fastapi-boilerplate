from datetime import timedelta

import pytest
from fastapi import HTTPException
from jose import jwt

from ..config import get_settings
from ..core.security import create_access_token, verify_password
from ..dependencies import get_current_user, get_db
from ..repositories.user_repository import UserRepository
from .utils import TestingSessionLocal, client, override_get_db, test_user  # noqa: F401

settings = get_settings()

app_module = None  # resolved below
from ..main import app  # noqa: E402

app.dependency_overrides[get_db] = override_get_db


# ── Unit tests ────────────────────────────────────────────────────────────────

def test_authenticate_user(test_user):  # noqa: F811
    db = TestingSessionLocal()
    repo = UserRepository(db)

    user = repo.get_by_username(test_user.username)
    assert user is not None
    assert verify_password("testpassword", user.hashed_password)

    assert repo.get_by_username("nonexistent_user") is None
    assert not verify_password("wrongpassword", user.hashed_password)


def test_create_access_token():
    token = create_access_token(
        {"sub": "testuser", "id": 1, "role": "user"},
        timedelta(days=1),
    )
    decoded = jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM],
        options={"verify_signature": False},
    )
    assert decoded["sub"] == "testuser"
    assert decoded["id"] == 1
    assert decoded["role"] == "user"


def test_get_current_user_valid_token():
    token = create_access_token({"sub": "testuser", "id": 1, "role": "admin"})
    user = get_current_user(token=token)
    assert user == {"username": "testuser", "id": 1, "user_role": "admin"}


def test_get_current_user_missing_payload():
    # Token is valid JWT but missing sub/id — should raise 401
    token = jwt.encode({"role": "user"}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(token=token)
    assert exc_info.value.status_code == 401


def test_get_current_user_invalid_token():
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(token="not.a.valid.token")
    assert exc_info.value.status_code == 401


# ── Integration tests ─────────────────────────────────────────────────────────

def test_register_user():
    response = client.post(
        "/auth/",
        json={
            "username": "newuser123",
            "email": "newuser@example.com",
            "first_name": "New",
            "last_name": "User",
            "password": "securePass123",
            "role": "user",
            "phone_number": "",
        },
    )
    assert response.status_code == 201
    # cleanup
    db = TestingSessionLocal()
    from ..models import Users
    db.query(Users).filter(Users.username == "newuser123").delete()
    db.commit()


def test_login_invalid_credentials():
    response = client.post(
        "/auth/token",
        data={"username": "nobody", "password": "wrong"},
    )
    assert response.status_code == 401
