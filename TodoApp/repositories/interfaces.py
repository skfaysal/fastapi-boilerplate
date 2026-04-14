"""
Repository interfaces — the "contract" every repository must honour.

Services import ONLY from this file, never from the concrete implementations.
That is what makes the template ORM-agnostic:

  - Want to use SQLAlchemy?  →  implement these ABCs with SQLAlchemy.
  - Want to use MongoDB?     →  implement these ABCs with PyMongo.
  - Want an in-memory store for tests?  →  implement these ABCs in pure Python.

The service layer never knows which one it is talking to.
"""
from abc import ABC, abstractmethod

from ..domain import TodoData, UserData


class AbstractUserRepository(ABC):

    @abstractmethod
    def get_by_id(self, user_id: int) -> UserData | None: ...

    @abstractmethod
    def get_by_username(self, username: str) -> UserData | None: ...

    @abstractmethod
    def get_by_email(self, email: str) -> UserData | None: ...

    @abstractmethod
    def create(self, data: UserData) -> UserData: ...

    @abstractmethod
    def save(self, data: UserData) -> UserData: ...


class AbstractTodoRepository(ABC):

    @abstractmethod
    def get_all_by_owner(self, owner_id: int) -> list[TodoData]: ...

    @abstractmethod
    def get_all(self) -> list[TodoData]: ...

    @abstractmethod
    def get_by_id(self, todo_id: int) -> TodoData | None: ...

    @abstractmethod
    def get_by_id_and_owner(self, todo_id: int, owner_id: int) -> TodoData | None: ...

    @abstractmethod
    def create(self, data: TodoData) -> TodoData: ...

    @abstractmethod
    def save(self, data: TodoData) -> TodoData: ...

    @abstractmethod
    def delete(self, data: TodoData) -> None: ...
