# Path, Query Parameters & Ordering in FastAPI

---

## Path Parameters

Declared directly in the route URL with `{name}`. FastAPI extracts and type-casts them automatically.

```python
@app.get("/books/{book_id}")
def get_book(book_id: int):   # FastAPI parses "42" → int 42
    ...
```

- Mandatory — the URL won't match without it.
- Type mismatch (e.g. `/books/abc`) → automatic **422 Unprocessable Entity**.

---

## Query Parameters

Any function parameter that is **not** in the path becomes a query param.

```python
@app.get("/books")
def list_books(author: str = None, limit: int = 10):
    ...
```

Called as: `GET /books?author=Martin&limit=5`

Use `Query(...)` from `fastapi` to add validation or docs:

```python
from fastapi import Query

def list_books(
    author: str | None = Query(None, description="Filter by author"),
    limit: int = Query(10, ge=1, le=100),
):
```

---

## `Query(...)` vs a plain default

| | Plain default | `Query(...)` |
|---|---|---|
| Marks param optional | `= None` | `= Query(None)` |
| Add description for `/docs` | No | Yes |
| Add validation (`ge`, `le`, `pattern`) | No | Yes |

Use a plain default for simple cases. Reach for `Query()` when you need constraints or docs.

---

## Route Ordering

FastAPI matches routes **top-to-bottom**. Put specific paths before parameterised ones.

```python
# GOOD — /books/popular is matched first
@app.get("/books/popular")
def popular_books(): ...

@app.get("/books/{book_id}")
def get_book(book_id: int): ...
```

```python
# BAD — "popular" gets swallowed by {book_id} and cast to int → 422
@app.get("/books/{book_id}")
def get_book(book_id: int): ...

@app.get("/books/popular")   # never reached
def popular_books(): ...
```

The same rule applies to methods on the same path — first matching decorator wins.

---

## Quick Reference

```
GET /books                      → list_books()        # no path param
GET /books?author=Martin        → list_books(author="Martin")
GET /books?sort_by=price&order=desc
GET /books/3                    → get_book(book_id=3) # path param
```
