"""Seed the `book` table with sample data.

Adds 10 books across 2 authors (5 each). Idempotent: skips a book if one with the
same title + author already exists, so it's safe to re-run.

Run:
    uv run python scripts/seed_books.py
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import select  # noqa: E402

from src.db.main import session_factory  # noqa: E402
from src.books.model import Book  # noqa: E402

# (title, author, year, price)
BOOKS = [
    # Robert C. Martin
    ("Clean Architecture", "Robert C. Martin", 2017, 34.99),
    ("The Clean Coder", "Robert C. Martin", 2011, 29.99),
    ("Agile Software Development, Principles, Patterns, and Practices", "Robert C. Martin", 2002, 49.99),
    ("Clean Agile: Back to Basics", "Robert C. Martin", 2019, 27.99),
    ("UML for Java Programmers", "Robert C. Martin", 2003, 39.99),
    # Martin Fowler
    ("Refactoring: Improving the Design of Existing Code", "Martin Fowler", 2018, 47.99),
    ("Patterns of Enterprise Application Architecture", "Martin Fowler", 2002, 54.99),
    ("Domain-Specific Languages", "Martin Fowler", 2010, 44.99),
    ("NoSQL Distilled", "Martin Fowler", 2012, 24.99),
    ("Analysis Patterns: Reusable Object Models", "Martin Fowler", 1996, 42.00),
]


async def main() -> None:
    added = 0
    async with session_factory() as session:
        for title, author, year, price in BOOKS:
            exists = await session.execute(
                select(Book).where(Book.title == title, Book.author == author)
            )
            if exists.scalars().first():
                continue
            session.add(Book(title=title, author=author, year=year, price=price))
            added += 1
        await session.commit()
    print(f"Seeded {added} new books ({len(BOOKS) - added} already existed).")


if __name__ == "__main__":
    asyncio.run(main())
