"""
SQLAlchemy implementation of AbstractTodoRepository.

This is the ONLY file in the project that knows about the Todos ORM model.
Everything above this layer (services, routers) works with TodoData dataclasses.

_to_data() is a private mapper that converts an ORM row → plain TodoData.
"""
from sqlalchemy.orm import Session

from ..domain import TodoData
from ..models import Todos
from .interfaces import AbstractTodoRepository


def _to_data(t: Todos) -> TodoData:
    return TodoData(
        id=t.id,
        title=t.title,
        description=t.description,
        priority=t.priority,
        complete=t.complete,
        owner_id=t.owner_id,
    )


class TodoRepository(AbstractTodoRepository):

    def __init__(self, db: Session) -> None:
        self._db = db

    def get_all_by_owner(self, owner_id: int) -> list[TodoData]:
        rows = self._db.query(Todos).filter(Todos.owner_id == owner_id).all()
        return [_to_data(t) for t in rows]

    def get_all(self) -> list[TodoData]:
        return [_to_data(t) for t in self._db.query(Todos).all()]

    def get_by_id(self, todo_id: int) -> TodoData | None:
        todo = self._db.get(Todos, todo_id)
        return _to_data(todo) if todo else None

    def get_by_id_and_owner(self, todo_id: int, owner_id: int) -> TodoData | None:
        todo = (
            self._db.query(Todos)
            .filter(Todos.id == todo_id, Todos.owner_id == owner_id)
            .first()
        )
        return _to_data(todo) if todo else None

    def create(self, data: TodoData) -> TodoData:
        todo = Todos(
            title=data.title,
            description=data.description,
            priority=data.priority,
            complete=data.complete,
            owner_id=data.owner_id,
        )
        self._db.add(todo)
        self._db.commit()
        self._db.refresh(todo)
        return _to_data(todo)  # returns with the real DB-assigned id

    def save(self, data: TodoData) -> TodoData:
        # Fetch the live ORM object, apply changes, persist.
        todo = self._db.get(Todos, data.id)
        todo.title = data.title
        todo.description = data.description
        todo.priority = data.priority
        todo.complete = data.complete
        self._db.commit()
        self._db.refresh(todo)
        return _to_data(todo)

    def delete(self, data: TodoData) -> None:
        todo = self._db.get(Todos, data.id)
        self._db.delete(todo)
        self._db.commit()
