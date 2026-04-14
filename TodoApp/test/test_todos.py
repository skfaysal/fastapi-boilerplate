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


def test_read_all_authenticated(test_todo):  # noqa: F811
    response = client.get("/")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == [
        {
            "complete": False,
            "title": "Learn to code!",
            "description": "Need to learn everyday!",
            "id": 1,
            "priority": 5,
            "owner_id": 1,
        }
    ]


def test_read_one_authenticated(test_todo):  # noqa: F811
    response = client.get("/todo/1")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "complete": False,
        "title": "Learn to code!",
        "description": "Need to learn everyday!",
        "id": 1,
        "priority": 5,
        "owner_id": 1,
    }


def test_read_one_not_found():
    response = client.get("/todo/999")
    assert response.status_code == 404


def test_create_todo(test_todo):  # noqa: F811
    payload = {
        "title": "New Todo!",
        "description": "New todo description",
        "priority": 5,
        "complete": False,
    }
    response = client.post("/todo", json=payload)
    assert response.status_code == 201

    db = TestingSessionLocal()
    model = db.query(Todos).filter(Todos.id == 2).first()
    assert model.title == payload["title"]
    assert model.description == payload["description"]
    assert model.priority == payload["priority"]
    assert model.complete == payload["complete"]


def test_update_todo(test_todo):  # noqa: F811
    payload = {
        "title": "Updated title",
        "description": "Need to learn everyday!",
        "priority": 5,
        "complete": False,
    }
    response = client.put("/todo/1", json=payload)
    assert response.status_code == 204

    db = TestingSessionLocal()
    model = db.query(Todos).filter(Todos.id == 1).first()
    assert model.title == "Updated title"


def test_update_todo_not_found():
    payload = {
        "title": "Updated title",
        "description": "Need to learn everyday!",
        "priority": 5,
        "complete": False,
    }
    response = client.put("/todo/999", json=payload)
    assert response.status_code == 404


def test_delete_todo(test_todo):  # noqa: F811
    response = client.delete("/todo/1")
    assert response.status_code == 204

    db = TestingSessionLocal()
    assert db.query(Todos).filter(Todos.id == 1).first() is None


def test_delete_todo_not_found():
    response = client.delete("/todo/999")
    assert response.status_code == 404
