from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.main import get_session
from src.dependencies import PaginationParams
from src.exceptions import NotFoundError
from src.schemas import Page
from src.auth.dependencies import get_current_user
from src.books.model import Book
from src.books.schema import BookCreate, BookUpdate
from src.books.service import BookService

# Every route on this router requires a valid access token. The dependency is
# declared here (not per-endpoint) so nothing can be added later that forgets it.
router = APIRouter(prefix="/books", tags=["books"], dependencies=[Depends(get_current_user)])


async def get_book_service(session: AsyncSession = Depends(get_session)) -> BookService:
    return BookService(session)


@router.get("", response_model=Page[Book])
async def list_books(
    pagination: PaginationParams = Depends(),
    author: str | None = Query(None, description="Filter by author (case-insensitive substring)"),
    service: BookService = Depends(get_book_service),
):
    items, total = await service.list_paginated(
        limit=pagination.limit,
        offset=pagination.offset,
        sort_by=pagination.sort_by,
        order=pagination.order,
        author=author,
    )
    return Page(items=items, total=total, limit=pagination.limit, offset=pagination.offset)


@router.get("/{book_id}", response_model=Book)
async def get_book(book_id: UUID, service: BookService = Depends(get_book_service)):
    book = await service.get_by_id(book_id)
    if not book:
        raise NotFoundError(f"Book {book_id} not found")
    return book


@router.post("", response_model=Book, status_code=201)
async def create_book(payload: BookCreate, service: BookService = Depends(get_book_service)):
    return await service.create(payload)


@router.put("/{book_id}", response_model=Book)
async def update_book(book_id: UUID, payload: BookUpdate, service: BookService = Depends(get_book_service)):
    book = await service.update(book_id, payload)
    if not book:
        raise NotFoundError(f"Book {book_id} not found")
    return book


@router.delete("/{book_id}", status_code=204)
async def delete_book(book_id: UUID, service: BookService = Depends(get_book_service)):
    deleted = await service.delete(book_id)
    if not deleted:
        raise NotFoundError(f"Book {book_id} not found")
