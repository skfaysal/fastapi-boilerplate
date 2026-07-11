from typing import Literal

from fastapi import Query


class PaginationParams:
    """Reusable pagination + sorting query params, injected with `Depends()`.

    Instead of repeating `limit`/`offset`/`sort_by`/`order` on every list endpoint,
    declare them once here and inject the bundled, validated object. This is the
    "dependency as a reusable gate" idea — a dependency doesn't have to return a
    service or a user, it can just be validated, structured input.

    Example:
        @router.get("")
        async def list_books(pagination: PaginationParams = Depends()): ...
    """

    def __init__(
        self,
        limit: int = Query(20, ge=1, le=100, description="Max items to return"),
        offset: int = Query(0, ge=0, description="Items to skip"),
        sort_by: str = Query("created_at", description="Field to sort by"),
        order: Literal["asc", "desc"] = Query("desc", description="Sort direction"),
    ):
        self.limit = limit
        self.offset = offset
        self.sort_by = sort_by
        self.order = order
