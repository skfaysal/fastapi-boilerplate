# FastAPI Boilerplate — Data Validation · Path/Query Params · Exception Handling
# Run:  uvicorn main:app --reload
# Docs: http://127.0.0.1:8000/docs

from typing import Optional
from fastapi import FastAPI, Path, Query, HTTPException
from pydantic import BaseModel, Field
from starlette import status

app = FastAPI()


# ── 1. DATA VALIDATION ───────────────────────────────────────────────────────
# Inherit BaseModel and use Field() to declare constraints.
# FastAPI validates the request body automatically → 422 on failure.
# Field constraints: min_length, max_length, gt, ge, lt, le, pattern

class BookRequest(BaseModel):
    id: Optional[int] = Field(default=None)   # omit on create
    title: str         = Field(min_length=3)
    rating: int        = Field(gt=0, lt=6)    # 1–5
    published_date: int = Field(gt=1999, lt=2031)

    model_config = {                           # prefills /docs "Try it out"
        "json_schema_extra": {
            "example": {"title": "Clean Code", "rating": 5, "published_date": 2008}
        }
    }


# ── Sample data ───────────────────────────────────────────────────────────────

class Book:
    def __init__(self, id, title, rating, published_date):
        self.id, self.title, self.rating, self.published_date = id, title, rating, published_date

BOOKS = [
    Book(1, "Clean Code", 5, 2008),
    Book(2, "Fluent Python", 5, 2022),
    Book(3, "Design Patterns", 4, 1994),
]


# ── 2. PATH PARAMETER VALIDATION ─────────────────────────────────────────────
# {book_id} in the route → extracted and type-coerced automatically.
# Path() adds extra constraints on top of the type hint → 422 on violation.
# Always put static routes (/books/all) BEFORE dynamic ones (/books/{id}).

@app.get("/books/{book_id}", status_code=status.HTTP_200_OK)
async def get_book(book_id: int = Path(gt=0)):
    for book in BOOKS:
        if book.id == book_id:
            return book
    # ── 3. EXCEPTION HANDLING ─────────────────────────────────────────────────
    # Raise HTTPException to return a proper HTTP error response.
    # detail can be a string, dict, or list — serialised to JSON.
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")


# ── 3. QUERY PARAMETER VALIDATION ────────────────────────────────────────────
# Params not in the path and not Body() → treated as query params (?key=val).
# Query() adds constraints the same way Path() does.
# Use Optional + default=None to make a param optional.

@app.get("/books", status_code=status.HTTP_200_OK)
async def get_books(
    rating: Optional[int] = Query(default=None, gt=0, lt=6),
):
    """Filter by rating: /books?rating=5  — omit to return all."""
    if rating:
        return [b for b in BOOKS if b.rating == rating]
    return BOOKS


# ── POST — body validated against BookRequest ─────────────────────────────────

@app.post("/books", status_code=status.HTTP_201_CREATED)
async def create_book(request: BookRequest):
    new_book = Book(
        id=BOOKS[-1].id + 1 if BOOKS else 1,
        title=request.title,
        rating=request.rating,
        published_date=request.published_date,
    )
    BOOKS.append(new_book)


# ── DELETE — path param + exception handling ──────────────────────────────────

@app.delete("/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_book(book_id: int = Path(gt=0)):
    for i, book in enumerate(BOOKS):
        if book.id == book_id:
            BOOKS.pop(i)
            return
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
