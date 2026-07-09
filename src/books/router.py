from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.main import get_session
from src.auth.dependencies import get_current_user
from src.books.model import Book
from src.books.schema import BookCreate, BookUpdate
from src.books.service import BookService

# Every route on this router requires a valid access token. The dependency is
# declared here (not per-endpoint) so nothing can be added later that forgets it.
router = APIRouter(prefix="/books", tags=["books"], dependencies=[Depends(get_current_user)])


async def get_book_service(session: AsyncSession = Depends(get_session)) -> BookService:
    return BookService(session)


@router.get("", response_model=list[Book])
async def list_books(service: BookService = Depends(get_book_service)):
    return await service.get_all()


@router.get("/{book_id}", response_model=Book)
async def get_book(book_id: UUID, service: BookService = Depends(get_book_service)):
    book = await service.get_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail=f"Book {book_id} not found")
    return book


@router.post("", response_model=Book, status_code=201)
async def create_book(payload: BookCreate, service: BookService = Depends(get_book_service)):
    return await service.create(payload)


@router.put("/{book_id}", response_model=Book)
async def update_book(book_id: UUID, payload: BookUpdate, service: BookService = Depends(get_book_service)):
    book = await service.update(book_id, payload)
    if not book:
        raise HTTPException(status_code=404, detail=f"Book {book_id} not found")
    return book


@router.delete("/{book_id}", status_code=204)
async def delete_book(book_id: UUID, service: BookService = Depends(get_book_service)):
    deleted = await service.delete(book_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Book {book_id} not found")
