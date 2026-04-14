from fastapi import status

from ..dependencies import get_current_user, get_db
from ..main import app
from .utils import (
    client,
    override_get_current_user,
    override_get_db,
    test_user,  # noqa: F401
)

app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user


def test_return_user(test_user):  # noqa: F811
    response = client.get("/user/")
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["username"] == "testuser"
    assert body["email"] == "testuser@example.com"
    assert body["first_name"] == "Test"
    assert body["last_name"] == "User"
    assert body["role"] == "admin"
    assert body["phone_number"] == "(111)-111-1111"


def test_change_password_success(test_user):  # noqa: F811
    response = client.put(
        "/user/password",
        json={"password": "testpassword", "new_password": "newpassword"},
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT


def test_change_password_wrong_current(test_user):  # noqa: F811
    response = client.put(
        "/user/password",
        json={"password": "wrongpassword", "new_password": "newpassword"},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_change_phone_number(test_user):  # noqa: F811
    response = client.put("/user/phonenumber/2222222222")
    assert response.status_code == status.HTTP_204_NO_CONTENT
