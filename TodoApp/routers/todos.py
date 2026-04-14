from fastapi import APIRouter, Path, status

from ..dependencies import CurrentUserDep, TodoServiceDep
from ..schemas.todo import TodoRequest, TodoResponse

router = APIRouter(tags=["todos"])


@router.get(
    "/",
    response_model=list[TodoResponse],
    summary="List my todos",
)
async def read_all(user: CurrentUserDep, service: TodoServiceDep) -> list[TodoResponse]:
    return service.get_all(user["id"])


@router.get(
    "/todo/{todo_id}",
    response_model=TodoResponse,
    summary="Get a single todo",
    responses={404: {"description": "Todo not found"}},
)
async def read_todo(
    user: CurrentUserDep,
    service: TodoServiceDep,
    todo_id: int = Path(gt=0),
) -> TodoResponse:
    return service.get_one(todo_id, user["id"])


@router.post(
    "/todo",
    status_code=status.HTTP_201_CREATED,
    summary="Create a todo",
)
async def create_todo(
    user: CurrentUserDep,
    service: TodoServiceDep,
    data: TodoRequest,
) -> None:
    service.create(data, user["id"])


@router.put(
    "/todo/{todo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Update a todo",
    responses={404: {"description": "Todo not found"}},
)
async def update_todo(
    user: CurrentUserDep,
    service: TodoServiceDep,
    data: TodoRequest,
    todo_id: int = Path(gt=0),
) -> None:
    service.update(todo_id, data, user["id"])


@router.delete(
    "/todo/{todo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a todo",
    responses={404: {"description": "Todo not found"}},
)
async def delete_todo(
    user: CurrentUserDep,
    service: TodoServiceDep,
    todo_id: int = Path(gt=0),
) -> None:
    service.delete(todo_id, user["id"])
