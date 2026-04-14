from ..core.errors import NotFoundError
from ..domain import TodoData
from ..repositories.interfaces import AbstractTodoRepository
from ..schemas.todo import TodoRequest


class TodoService:
    def __init__(self, repo: AbstractTodoRepository) -> None:
        self._repo = repo

    def get_all(self, owner_id: int) -> list[TodoData]:
        return self._repo.get_all_by_owner(owner_id)

    def get_all_admin(self) -> list[TodoData]:
        return self._repo.get_all()

    def get_one(self, todo_id: int, owner_id: int) -> TodoData:
        todo = self._repo.get_by_id_and_owner(todo_id, owner_id)
        if not todo:
            raise NotFoundError(f"Todo {todo_id} not found.")
        return todo

    def create(self, data: TodoRequest, owner_id: int) -> TodoData:
        return self._repo.create(TodoData(
            id=0,  # DB assigns the real id
            title=data.title,
            description=data.description,
            priority=data.priority,
            complete=data.complete,
            owner_id=owner_id,
        ))

    def update(self, todo_id: int, data: TodoRequest, owner_id: int) -> TodoData:
        todo = self.get_one(todo_id, owner_id)  # TodoData
        # Mutate the dataclass, then hand it back to the repo to persist.
        todo.title = data.title
        todo.description = data.description
        todo.priority = data.priority
        todo.complete = data.complete
        return self._repo.save(todo)

    def delete(self, todo_id: int, owner_id: int) -> None:
        todo = self.get_one(todo_id, owner_id)
        self._repo.delete(todo)

    def delete_admin(self, todo_id: int) -> None:
        todo = self._repo.get_by_id(todo_id)
        if not todo:
            raise NotFoundError(f"Todo {todo_id} not found.")
        self._repo.delete(todo)
