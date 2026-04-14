from fastapi import APIRouter, Depends, Path, status

from ..dependencies import TodoServiceDep, require_admin
from ..schemas.todo import TodoResponse

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin)],  # enforced for every route in this router
)


@router.get(
    "/todo",
    response_model=list[TodoResponse],
    summary="Admin — list all todos",
    responses={403: {"description": "Admin role required"}},
)
async def read_all(service: TodoServiceDep) -> list[TodoResponse]:
    return service.get_all_admin()


@router.delete(
    "/todo/{todo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Admin — delete any todo",
    responses={
        403: {"description": "Admin role required"},
        404: {"description": "Todo not found"},
    },
)
async def delete_todo(service: TodoServiceDep, todo_id: int = Path(gt=0)) -> None:
    service.delete_admin(todo_id)
