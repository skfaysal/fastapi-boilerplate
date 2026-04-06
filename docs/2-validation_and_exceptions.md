# Data Validation, Parameter Validation & Exception Handling

> Study note for `main.py` — covers all three topics compactly.

---

## 1. Data Validation — Pydantic + `Field()`

Pydantic validates the **request body** automatically. Declare a `BaseModel` subclass and use it as a function parameter type hint.

```python
from pydantic import BaseModel, Field
from typing import Optional

class BookRequest(BaseModel):
    id: Optional[int] = Field(default=None)   # optional
    title: str        = Field(min_length=3)
    rating: int       = Field(gt=0, lt=6)     # 1–5
    year: int         = Field(ge=2000, le=2030)
```

```python
@app.post("/books", status_code=201)
async def create_book(book: BookRequest):   # body parsed & validated here
    ...
```

### Field constraint cheat-sheet

| Constraint | Meaning |
|---|---|
| `min_length` / `max_length` | string length |
| `gt` / `ge` | greater than / greater-or-equal |
| `lt` / `le` | less than / less-or-equal |
| `pattern` | regex match |
| `default` | makes field optional |

### What happens on failure

FastAPI returns **422 Unprocessable Entity** with a JSON body listing every field error — automatically, no extra code.

### Swagger example

Add `model_config` to pre-fill the "Try it out" body in `/docs`:

```python
model_config = {
    "json_schema_extra": {
        "example": {"title": "Clean Code", "rating": 5, "year": 2008}
    }
}
```

---

## 2. Path Parameter Validation — `Path()`

Path params are URL segments declared with `{name}` in the route string.

```python
from fastapi import Path

@app.get("/books/{book_id}")
async def get_book(book_id: int = Path(gt=0)):
    ...
```

- The **type hint** (`int`) coerces the string segment → integer.
- `Path()` adds extra constraints on top of the type.
- FastAPI returns **422** automatically if the constraint fails.

### Common `Path()` constraints

```python
Path(gt=0)                   # positive int
Path(ge=1, le=100)           # 1–100 inclusive
Path(min_length=1)           # non-empty string
Path(pattern=r"^\d{4}$")     # 4-digit string
```

### Static vs dynamic route order — critical rule

FastAPI matches routes **top to bottom**. Always put static routes before dynamic ones:

```python
@app.get("/books/featured")      # ← must come FIRST
async def featured(): ...

@app.get("/books/{book_id}")     # ← catches everything else
async def get_book(book_id: int = Path(gt=0)): ...
```

If `{book_id}` is registered first, `/books/featured` is captured as `book_id="featured"` and fails the `int` coercion.

---

## 3. Query Parameter Validation — `Query()`

Query params live after `?` in the URL: `/books?rating=5&year=2008`.

Any function parameter that is **not** a path param and **not** a `Body()` is automatically a query param.

```python
from fastapi import Query

@app.get("/books/filter")
async def filter_books(rating: int = Query(gt=0, lt=6)):
    ...
```

### Required vs optional

```python
rating: int = Query(gt=0, lt=6)                        # required
rating: Optional[int] = Query(default=None, gt=0, lt=6) # optional
```

### Multiple optional filters

```python
async def search(
    author: Optional[str] = Query(default=None, min_length=1),
    min_rating: Optional[int] = Query(default=None, gt=0, lt=6),
):
    ...
# Usage: /books/filter/search?author=GoF&min_rating=4
```

### Path vs Query — when to use which

| Use **path** when | Use **query** when |
|---|---|
| Param identifies the resource | Param filters/modifies the result |
| `/books/42` | `/books?rating=5` |
| Always required | Optional |

---

## 4. Exception Handling — `HTTPException`

Raise `HTTPException` to return a proper HTTP error response.

```python
from fastapi import HTTPException
from starlette import status

raise HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="Book not found"
)
```

`detail` can be a string, dict, or list — serialised to JSON automatically.

### Common status codes

```python
status.HTTP_200_OK            # 200
status.HTTP_201_CREATED       # 201 — use on successful POST
status.HTTP_204_NO_CONTENT    # 204 — success, no body (DELETE/PUT)
status.HTTP_400_BAD_REQUEST   # 400 — malformed request
status.HTTP_404_NOT_FOUND     # 404 — resource doesn't exist
status.HTTP_422_UNPROCESSABLE_ENTITY  # 422 — auto-raised by FastAPI on validation failure
```

### Custom global exception handler

Override how any exception type is formatted across the whole app:

```python
from fastapi import Request
from fastapi.responses import JSONResponse

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "path": request.url.path}
    )
```

### Custom exception class

```python
class ItemNotFoundError(Exception):
    def __init__(self, item_id: int):
        self.item_id = item_id

@app.exception_handler(ItemNotFoundError)
async def item_not_found_handler(request: Request, exc: ItemNotFoundError):
    return JSONResponse(status_code=404, content={"message": f"Item {exc.item_id} not found"})

# Raise it in any endpoint:
raise ItemNotFoundError(item_id=42)
```

---

## 5. How They Work Together

```
Incoming request
    │
    ├─ Path params extracted & type-coerced → Path() constraints checked → 422 if invalid
    ├─ Query params extracted & type-coerced → Query() constraints checked → 422 if invalid
    ├─ Body parsed as JSON → Pydantic model validated → 422 if invalid
    │
    └─ Endpoint function called
           └─ Business logic runs
                  └─ HTTPException raised → error response returned
                  └─ return value → 2xx response with JSON body
```

FastAPI handles all validation **before** your function runs. You only need to raise `HTTPException` for logic-level errors (not found, conflict, forbidden, etc.).

---

## Quick Reference

```python
# Imports you'll need
from fastapi import FastAPI, Path, Query, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from starlette import status

# Body validation
class MyModel(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    score: int = Field(ge=0, le=100)

# Path param validation
@app.get("/items/{item_id}")
async def get_item(item_id: int = Path(gt=0)): ...

# Query param validation
@app.get("/items")
async def list_items(score: Optional[int] = Query(default=None, ge=0, le=100)): ...

# Exception
raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
```
