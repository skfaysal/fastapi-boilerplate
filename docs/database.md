# Database Setup with SQLModel & SQLAlchemy

---

## What is an ORM?

An ORM (Object Relational Mapper) lets you work with database tables as Python classes instead of writing raw SQL.

Without ORM:
```sql
INSERT INTO book (title, author) VALUES ('Clean Code', 'Martin');
SELECT * FROM book WHERE id = 1;
```

With SQLModel:
```python
book = Book(title="Clean Code", author="Martin")
session.add(book)
session.commit()
```

SQLModel sits on top of SQLAlchemy (the ORM engine) and Pydantic (validation). One class does both.

---

## The Engine

The engine is the single connection point between Python and your database. You create it once at startup.

```python
from sqlalchemy.ext.asyncio import create_async_engine

async_engine = create_async_engine(url="postgresql+asyncpg://user:pass@localhost/dbname")
```

- `postgresql+asyncpg` — postgres database, asyncpg is the async driver
- `echo=True` — prints every SQL query to the console (useful during dev)

The engine doesn't open a connection immediately — it creates a **connection pool** and hands out connections on demand.

---

## Session

A session is a single unit of work with the database — think of it as a shopping basket. You collect operations (add, update, delete), then commit them all at once.

```python
session_factory = async_sessionmaker(bind=async_engine, expire_on_commit=False)

async with session_factory() as session:
    session.add(book)
    await session.commit()
```

---

## Defining a Table

Any SQLModel class with `table=True` maps directly to a database table.

```python
from sqlmodel import SQLModel, Field
from uuid import UUID, uuid4

class Book(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    title: str
    author: str
    year: int
    price: float
```

- Class name → table name (`book`)
- Each field → a column with the matching type
- `primary_key=True` → the unique identifier for each row
- `default_factory=uuid4` → auto-generates a UUID if no id is provided

---

## Creating Tables on Startup

`SQLModel.metadata` tracks all classes with `table=True`. Calling `create_all` sends `CREATE TABLE IF NOT EXISTS` to the database.

```python
async def init_db():
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
```

This runs inside FastAPI's `lifespan` so the table exists before the first request hits.

> The model file must be imported before `init_db()` is called — otherwise the metadata doesn't know the table exists yet. That's why `src/main.py` imports `model` before calling `init_db`.
