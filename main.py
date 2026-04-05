# =============================================================================
# FastAPI Boilerplate — Books API
# =============================================================================
# HOW TO RUN:
#   uvicorn main:app --reload
#
# Interactive API docs (auto-generated):
#   http://127.0.0.1:8000/docs      ← Swagger UI
#   http://127.0.0.1:8000/redoc     ← ReDoc
# =============================================================================

from fastapi import FastAPI, Body

# -----------------------------------------------------------------------------
# Application Instance
# -----------------------------------------------------------------------------
# FastAPI() creates the ASGI application object.
# Under the hood it initializes Starlette (routing, middleware, exception
# handling) and its own OpenAPI/JSON-Schema machinery.
# All route decorators (@app.get, @app.post …) register handlers on this
# object's internal router.
# -----------------------------------------------------------------------------
app = FastAPI(
    title="Books API",
    description="FastAPI boilerplate demonstrating all HTTP methods, path params, query params, and request bodies.",
    version="1.0.0",
)


# =============================================================================
# In-memory data store (stands in for a real database)
# =============================================================================
BOOKS = [
    {"title": "Title One",   "author": "Author One", "category": "science"},
    {"title": "Title Two",   "author": "Author Two", "category": "science"},
    {"title": "Title Three", "author": "Author Three","category": "history"},
    {"title": "Title Four",  "author": "Author Four", "category": "math"},
    {"title": "Title Five",  "author": "Author Five", "category": "math"},
    {"title": "Title Six",   "author": "Author Two",  "category": "math"},
]


# =============================================================================
# GET — Read / Retrieve data
# =============================================================================
# USE WHEN: You want to fetch data without changing server state.
# Safe & idempotent: calling it multiple times has no side-effects.
# Data is passed via the URL (path params or query params), never in the body.
# =============================================================================


# --- Basic GET (no parameters) -----------------------------------------------
# Matches: GET /
# Returns a simple health-check / welcome message.
@app.get("/")
async def root():
    return {"message": "Welcome to the Books API. Visit /docs for usage."}


# --- GET all books -----------------------------------------------------------
# Matches: GET /books
@app.get("/books")
async def get_all_books():
    return BOOKS


# --- GET with PATH PARAMETER -------------------------------------------------
# Path parameters are variable segments embedded directly in the URL path.
# Declare them with {curly_braces} in the route and as function arguments.
#
# IMPORTANT — ORDER MATTERS:
#   FastAPI matches routes top-to-bottom. Always put STATIC routes (e.g.
#   /books/mybook) BEFORE dynamic routes (/books/{book_title}), otherwise
#   the dynamic route will swallow the static one.
#
# URL example:  GET /books/Title%20One   (%20 = space)
@app.get("/books/{book_title}")
async def get_book_by_title(book_title: str):
    """Return a single book whose title matches (case-insensitive)."""
    for book in BOOKS:
        if book.get("title").casefold() == book_title.casefold():
            return book
    return {"error": f"Book '{book_title}' not found."}


# --- GET with QUERY PARAMETER ------------------------------------------------
# Query parameters appear after "?" as key=value pairs.
# They are optional by default when given a default value (e.g. category="").
# They are REQUIRED when no default is provided.
#
# URL example:  GET /books/?category=math
#
# NOTE: The trailing slash on "/books/" makes this route distinct from
# "/books" above. FastAPI differentiates them.
@app.get("/books/")
async def get_books_by_category(category: str):
    """Return all books in a given category (query param)."""
    return [
        book for book in BOOKS
        if book.get("category").casefold() == category.casefold()
    ]


# --- GET combining PATH + QUERY parameters -----------------------------------
# You can mix both: path param captures part of the URL; query param comes
# after "?".
#
# URL example:  GET /books/Author%20Two/?category=math
@app.get("/books/{book_author}/")
async def get_books_by_author_and_category(book_author: str, category: str):
    """Return books filtered by author (path) AND category (query)."""
    return [
        book for book in BOOKS
        if book.get("author").casefold() == book_author.casefold()
        and book.get("category").casefold() == category.casefold()
    ]


# =============================================================================
# POST — Create new data
# =============================================================================
# USE WHEN: You want to CREATE a new resource.
# NOT idempotent: calling it twice creates two entries.
# Data is sent in the REQUEST BODY (JSON), not in the URL.
# Response conventionally returns 201 Created (FastAPI defaults to 200).
#
# Example request body (JSON):
#   {"title": "Title Seven", "author": "Author Seven", "category": "biology"}
# =============================================================================
@app.post("/books/create_book", status_code=201)
async def create_book(new_book: dict = Body()):
    """
    Create a new book entry.

    Send a JSON body:
        {
            "title": "My New Book",
            "author": "Some Author",
            "category": "fiction"
        }
    """
    BOOKS.append(new_book)
    return {"message": "Book created successfully.", "book": new_book}


# =============================================================================
# PUT — Full Update / Replace a resource
# =============================================================================
# USE WHEN: You want to REPLACE an entire resource with new data.
# Idempotent: sending the same request multiple times produces the same result.
# The client sends the COMPLETE representation of the resource.
# Contrast with PATCH (partial update).
#
# Example request body:
#   {"title": "Title One", "author": "Updated Author", "category": "physics"}
# =============================================================================
@app.put("/books/update_book")
async def update_book(updated_book: dict = Body()):
    """
    Fully replace a book record matched by title.

    Send the complete updated book as a JSON body (title is used as the key).
    """
    for i, book in enumerate(BOOKS):
        if book.get("title").casefold() == updated_book.get("title").casefold():
            BOOKS[i] = updated_book
            return {"message": "Book updated.", "book": BOOKS[i]}
    return {"error": "Book not found."}


# =============================================================================
# PATCH — Partial Update
# =============================================================================
# USE WHEN: You want to update ONLY specific fields of a resource, not replace
# the whole thing. More efficient than PUT when only one field changes.
# Idempotent in practice (should be designed that way).
#
# Example request body:
#   {"title": "Title One", "category": "physics"}
#   ↑ only 'category' changes; 'author' is preserved.
# =============================================================================
@app.patch("/books/patch_book")
async def patch_book(patch_data: dict = Body()):
    """
    Partially update a book. Only the fields provided are changed.

    'title' is used as the lookup key and must be included.
    """
    for i, book in enumerate(BOOKS):
        if book.get("title").casefold() == patch_data.get("title", "").casefold():
            BOOKS[i] = {**book, **patch_data}   # merge: existing fields + updates
            return {"message": "Book patched.", "book": BOOKS[i]}
    return {"error": "Book not found."}


# =============================================================================
# DELETE — Remove a resource
# =============================================================================
# USE WHEN: You want to DELETE a resource permanently.
# Idempotent: deleting something that's already gone should still return 200/204.
# The resource is identified via path or query parameters (not a body).
# =============================================================================
@app.delete("/books/delete_book/{book_title}")
async def delete_book(book_title: str):
    """Delete the book whose title matches the path parameter."""
    for i, book in enumerate(BOOKS):
        if book.get("title").casefold() == book_title.casefold():
            deleted = BOOKS.pop(i)
            return {"message": "Book deleted.", "book": deleted}
    return {"error": f"Book '{book_title}' not found."}


# =============================================================================
# QUICK REFERENCE — HTTP Methods
# =============================================================================
#
#  Method  | CRUD   | Has Body | Idempotent | Safe | Common Status Codes
#  ---------|--------|----------|------------|------|---------------------
#  GET      | Read   | No       | Yes        | Yes  | 200, 404
#  POST     | Create | Yes      | No         | No   | 201, 400
#  PUT      | Update | Yes      | Yes        | No   | 200, 404
#  PATCH    | Update | Yes      | Yes*       | No   | 200, 404
#  DELETE   | Delete | No       | Yes        | No   | 200, 204, 404
#
# Safe      = Does not modify server state
# Idempotent = Same request N times == same result as 1 time
# =============================================================================
