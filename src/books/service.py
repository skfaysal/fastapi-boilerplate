from uuid import UUID

from sqlalchemy import asc, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.books.model import Book, utcnow
from src.books.schema import BookCreate, BookUpdate

# Whitelist of sortable columns — never getattr() an arbitrary client string onto the model.
_SORTABLE = {"created_at", "title", "author", "year", "price"}


class BookService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all(self) -> list[Book]:
        result = await self.session.execute(select(Book))
        return result.scalars().all()

    async def list_paginated(
        self, *, limit: int, offset: int, sort_by: str, order: str, author: str | None = None,
    ) -> tuple[list[Book], int]:
        """Return one page of books plus the total count (for the Page envelope).

        Filtering (`author` substring), sorting (whitelisted column + direction) and
        pagination (`limit`/`offset`) are the three conventions every list endpoint reuses.
        """
        conditions = []
        if author:
            conditions.append(Book.author.ilike(f"%{author}%"))

        column = getattr(Book, sort_by if sort_by in _SORTABLE else "created_at")
        direction = desc if order == "desc" else asc

        page_query = (
            select(Book).where(*conditions).order_by(direction(column)).limit(limit).offset(offset)
        )
        items = (await self.session.execute(page_query)).scalars().all()

        count_query = select(func.count()).select_from(Book).where(*conditions)
        total = (await self.session.execute(count_query)).scalar_one()
        return items, total

    async def get_by_id(self, book_id: UUID) -> Book | None:
        return await self.session.get(Book, book_id)

    async def create(self, payload: BookCreate) -> Book:
        book = Book(**payload.model_dump())
        self.session.add(book)
        await self.session.commit()
        await self.session.refresh(book)
        return book

    async def update(self, book_id: UUID, payload: BookUpdate) -> Book | None:
        book = await self.session.get(Book, book_id)
        if not book:
            return None
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(book, key, value)
        book.updated_at = utcnow()
        self.session.add(book)
        await self.session.commit()
        await self.session.refresh(book)
        return book

    async def delete(self, book_id: UUID) -> bool:
        book = await self.session.get(Book, book_id)
        if not book:
            return False
        await self.session.delete(book)
        await self.session.commit()
        return True
