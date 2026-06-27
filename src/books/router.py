from fastapi import APIRouter, HTTPException

from .schema import Book, BookCreate, BookUpdate
from .book_data import book_store, next_id

router = APIRouter(prefix="/books", tags=["books"])


@router.get("", response_model=list[Book])
def list_books():
    return list(book_store.values())


@router.get("/{book_id}", response_model=Book)
def get_book(book_id: int):
    book = book_store.get(book_id)
    if not book:
        raise HTTPException(status_code=404, detail=f"Book {book_id} not found")
    return book


@router.post("", response_model=Book, status_code=201)
def create_book(payload: BookCreate):
    book_id = next_id()
    book = {"id": book_id, **payload.model_dump()}
    book_store[book_id] = book
    return book


@router.put("/{book_id}", response_model=Book)
def update_book(book_id: int, payload: BookUpdate):
    book = book_store.get(book_id)
    if not book:
        raise HTTPException(status_code=404, detail=f"Book {book_id} not found")
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    book_store[book_id] = {**book, **updates}
    return book_store[book_id]


@router.delete("/{book_id}", status_code=204)
def delete_book(book_id: int):
    if book_id not in book_store:
        raise HTTPException(status_code=404, detail=f"Book {book_id} not found")
    del book_store[book_id]
