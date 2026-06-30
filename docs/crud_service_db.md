# CRUD with DB, Services & Dependency Injection

---

## The Layered Pattern

```
router.py   →   service.py   →   database
(HTTP)          (business)       (SQLAlchemy)
```

- **Router** handles HTTP — paths, status codes, raising 404s
- **Service** handles DB logic — queries, commits, business rules
- **DB** handles persistence

Keeping them separate means the router never touches SQL and the service never knows about HTTP.

---

## Service Class

The service takes a `session` in `__init__` and uses it for all DB operations.

```python
class BookService:
    def __init__(self, session: AsyncSession):
        self.session = session
```

### Core DB operations

**Read all**
```python
result = await self.session.execute(select(Book))
return result.scalars().all()
```
`select(Book)` builds a `SELECT * FROM book` query. `.scalars().all()` extracts the rows as a list of `Book` objects.

**Read one by id**
```python
book = await self.session.get(Book, book_id)
```
Fetches by primary key directly — no need to write a `WHERE` clause.

**Create**
```python
book = Book(**payload.model_dump())
self.session.add(book)
await self.session.commit()
await self.session.refresh(book)
```
- `add` — stages the object (no SQL yet)
- `commit` — writes to DB
- `refresh` — re-reads the row from DB so fields like `created_at` are populated on the returned object

**Update**
```python
for key, value in payload.model_dump(exclude_unset=True).items():
    setattr(book, key, value)
await self.session.commit()
await self.session.refresh(book)
```
`exclude_unset=True` only includes fields the client actually sent — skips fields they left out. No need to `add()` again since the object is already tracked by the session.

**Delete**
```python
await self.session.delete(book)
await self.session.commit()
```

---

## Dependency Injection

FastAPI's `Depends` runs a function and injects its return value into the endpoint.

```python
# 1. get_session yields a DB session (defined in db/main.py)
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with session_factory() as session:
        yield session

# 2. get_book_service takes that session and returns a BookService
async def get_book_service(session: AsyncSession = Depends(get_session)) -> BookService:
    return BookService(session)

# 3. Endpoint receives the ready-to-use service
async def list_books(service: BookService = Depends(get_book_service)):
    return await service.get_all()
```

FastAPI resolves the chain automatically — you only declare what you need, it figures out what to call first.

`get_session` uses `yield` instead of `return` — this is a context manager pattern. Code before `yield` runs before the request, code after `yield` (cleanup) runs after the response is sent.

---

## Why async?

DB calls involve waiting — network round trips to postgres. `async/await` lets the server handle other requests while waiting instead of blocking.

Every method that touches the DB must be `async def` and every DB call must be `await`ed.
