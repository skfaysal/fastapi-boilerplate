from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.books.model import Book, utcnow
from src.books.schema import BookCreate, BookUpdate


class BookService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all(self) -> list[Book]:
        result = await self.session.execute(select(Book))
        return result.scalars().all()

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
