from fastapi import status

from ..dependencies import get_current_user, get_db
from ..main import app
from ..models import Todos
from .utils import (
    TestingSessionLocal,
    client,
    override_get_current_user,
    override_get_db,
    test_todo,  # noqa: F401
    test_user,  # noqa: F401
)

app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user


def test_admin_read_all(test_todo):  # noqa: F811
    response = client.get("/admin/todo")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) >= 1
    assert data[0]["title"] == "Learn to code!"


def test_admin_delete_todo(test_todo):  # noqa: F811
    response = client.delete("/admin/todo/1")
    assert response.status_code == 204

    db = TestingSessionLocal()
    assert db.query(Todos).filter(Todos.id == 1).first() is None


def test_admin_delete_todo_not_found():
    response = client.delete("/admin/todo/9999")
    assert response.status_code == 404
