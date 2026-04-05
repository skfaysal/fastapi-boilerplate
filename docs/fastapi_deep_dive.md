# FastAPI Deep Dive — Complete Study Material

> Companion to `main.py` in this repository.
> Covers everything from `app = FastAPI()` internals to running with Uvicorn.

---

## Table of Contents

1. [What is FastAPI?](#1-what-is-fastapi)
2. [Under the Hood: `app = FastAPI()`](#2-under-the-hood-app--fastapi)
3. [Under the Hood: `@app.get(...)` — Route Decorators](#3-under-the-hood-appget--route-decorators)
4. [HTTP Methods — When to Use What](#4-http-methods--when-to-use-what)
   - [GET](#41-get)
   - [POST](#42-post)
   - [PUT](#43-put)
   - [PATCH](#44-patch)
   - [DELETE](#45-delete)
5. [Path Parameters](#5-path-parameters)
6. [Query Parameters](#6-query-parameters)
7. [Request Body (`Body()`)](#7-request-body-body)
8. [Combining Path, Query, and Body](#8-combining-path-query-and-body)
9. [Status Codes](#9-status-codes)
10. [Auto-Generated Docs (Swagger & ReDoc)](#10-auto-generated-docs-swagger--redoc)
11. [How to Run: Uvicorn — What It Is and Why](#11-how-to-run-uvicorn--what-it-is-and-why)
12. [Mental Model: Full Request Lifecycle](#12-mental-model-full-request-lifecycle)

---

## 1. What is FastAPI?

FastAPI is a **modern Python web framework** for building APIs. Its three core promises:

| Promise | How |
|---|---|
| **Fast to run** | Built on ASGI (async by default); benchmarks near Node.js and Go |
| **Fast to develop** | Very little boilerplate; Python type hints drive everything |
| **Automatic docs** | OpenAPI schema generated at startup — zero extra work |

FastAPI is not written from scratch. It is a thin, opinionated layer on top of two libraries:

```
Your code
    └── FastAPI          ← routing, dependency injection, validation, OpenAPI
          └── Starlette  ← ASGI toolkit (requests, responses, middleware, WebSocket)
                └── Uvicorn / any ASGI server
```

---

## 2. Under the Hood: `app = FastAPI()`

```python
app = FastAPI()
```

This one line does a lot. Here is what happens internally:

### 2.1 Starlette Application is Created

`FastAPI` inherits directly from `Starlette`. When you call `FastAPI()`, it calls `Starlette.__init__()` which sets up:

- **Router** (`APIRouter`) — an internal routing table (list of routes)
- **Middleware stack** — a chain of callables that wrap every request/response
- **Exception handlers** — maps exception types to response-producing functions
- **Lifespan context** — startup/shutdown hooks (new in Starlette 0.20+)

### 2.2 OpenAPI Machinery is Initialized

FastAPI adds its own layer on top of Starlette:

- An **OpenAPI schema dict** is prepared (populated lazily on first `/docs` visit)
- Routes for `/docs` (Swagger UI), `/redoc`, and `/openapi.json` are registered automatically
- A **JSON Schema** generator is configured (powered by Pydantic)

### 2.3 The Object is an ASGI App

The resulting `app` object is an **ASGI callable** — it implements the interface:

```python
async def __call__(self, scope, receive, send): ...
```

This is the contract that Uvicorn (or any ASGI server) will call for every incoming HTTP connection. `scope` describes the request, `receive` yields request body chunks, `send` accepts response chunks.

### 2.4 Optional Constructor Arguments

```python
app = FastAPI(
    title="My API",          # shown in /docs header
    description="...",       # shown in /docs
    version="1.0.0",         # shown in /docs
    docs_url="/docs",        # change or disable Swagger path
    redoc_url="/redoc",      # change or disable ReDoc path
    openapi_url="/openapi.json",
)
```

---

## 3. Under the Hood: `@app.get(...)` — Route Decorators

```python
@app.get("/books")
async def get_all_books():
    return BOOKS
```

### 3.1 What a Decorator Is (Python Refresher)

The `@` syntax is syntactic sugar for:

```python
def get_all_books():
    return BOOKS

get_all_books = app.get("/books")(get_all_books)
```

`app.get("/books")` returns a **decorator factory** — a function that, when called with `get_all_books`, registers the route and returns the original function unchanged (so you can still call it directly in tests).

### 3.2 What Happens at Registration Time (import time)

When Python imports `main.py`, every `@app.get(...)` line executes immediately. FastAPI:

1. Creates a `Route` object containing:
   - The **path** (`"/books"`)
   - The **HTTP method** (`GET`)
   - The **endpoint function** (`get_all_books`)
   - Introspected **parameter metadata** (from type hints and `Body()`)
2. Adds the `Route` to the internal `Router.routes` list
3. Updates the **OpenAPI schema** with this route's operation object

### 3.3 What Happens at Request Time (runtime)

When a `GET /books` request arrives:

```
Uvicorn
  → ASGI __call__(scope, receive, send)
    → Middleware stack (CORS, auth, logging…)
      → Router.handle(request)
        → Route match: "/books" + GET → get_all_books
          → Dependency injection (if any)
            → Parameter extraction & validation (Pydantic)
              → await get_all_books()
                → Response serialization (JSON)
                  → HTTP response sent back
```

### 3.4 The Five Route Decorator Methods

| Decorator | HTTP Method |
|---|---|
| `@app.get(path)` | GET |
| `@app.post(path)` | POST |
| `@app.put(path)` | PUT |
| `@app.patch(path)` | PATCH |
| `@app.delete(path)` | DELETE |

All accept the same keyword arguments: `status_code`, `tags`, `summary`, `description`, `response_model`, `deprecated`, etc.

---

## 4. HTTP Methods — When to Use What

HTTP methods express **intent**. Choosing the right method is part of REST design.

### 4.1 GET

**Purpose:** Retrieve data. Never modify anything.

```python
@app.get("/books")
async def get_all_books():
    return BOOKS
```

| Property | Value |
|---|---|
| Has request body | No |
| Safe | Yes (read-only) |
| Idempotent | Yes |
| Typical status codes | 200 OK, 404 Not Found |

**Rules:**
- Parameters go in the **URL** (path or query string), never the body.
- Results can be cached by browsers and CDNs.
- Use for listing resources, fetching a single item, searching/filtering.

---

### 4.2 POST

**Purpose:** Create a new resource.

```python
@app.post("/books/create_book", status_code=201)
async def create_book(new_book: dict = Body()):
    BOOKS.append(new_book)
    return new_book
```

| Property | Value |
|---|---|
| Has request body | Yes |
| Safe | No |
| Idempotent | No (each call creates a new record) |
| Typical status codes | 201 Created, 400 Bad Request, 422 Unprocessable Entity |

**Rules:**
- The body contains the **full new resource**.
- The server decides the new resource's ID (vs. PUT where the client specifies it).
- Calling POST twice = two records created.

---

### 4.3 PUT

**Purpose:** Fully replace an existing resource.

```python
@app.put("/books/update_book")
async def update_book(updated_book: dict = Body()):
    # replaces the matched book entirely
```

| Property | Value |
|---|---|
| Has request body | Yes |
| Safe | No |
| Idempotent | Yes (same request → same final state) |
| Typical status codes | 200 OK, 404 Not Found |

**Rules:**
- Client sends the **complete** resource — all fields.
- Any field not included is considered removed/reset.
- Contrast with PATCH: PUT is "replace everything", PATCH is "change only these fields".

---

### 4.4 PATCH

**Purpose:** Partially update a resource.

```python
@app.patch("/books/patch_book")
async def patch_book(patch_data: dict = Body()):
    # only fields in patch_data are updated; others remain unchanged
    BOOKS[i] = {**book, **patch_data}
```

| Property | Value |
|---|---|
| Has request body | Yes (partial) |
| Safe | No |
| Idempotent | Yes (should be designed this way) |
| Typical status codes | 200 OK, 404 Not Found |

**When to prefer PATCH over PUT:**
- Changing just one field (e.g., update email without sending the entire user object).
- Bandwidth-sensitive clients (mobile apps).
- When not sending all fields could accidentally wipe data.

---

### 4.5 DELETE

**Purpose:** Remove a resource.

```python
@app.delete("/books/delete_book/{book_title}")
async def delete_book(book_title: str):
    BOOKS.pop(i)
```

| Property | Value |
|---|---|
| Has request body | No (identify via path param) |
| Safe | No |
| Idempotent | Yes (deleting a non-existent resource is still a valid outcome) |
| Typical status codes | 200 OK (with body), 204 No Content (no body), 404 Not Found |

---

### 4.6 Quick Reference Table

```
Method | CRUD   | Body? | Idempotent | Safe | Common Codes
-------|--------|-------|------------|------|-------------
GET    | Read   | No    | Yes        | Yes  | 200, 404
POST   | Create | Yes   | No         | No   | 201, 400, 422
PUT    | Update | Yes   | Yes        | No   | 200, 404
PATCH  | Update | Yes*  | Yes        | No   | 200, 404
DELETE | Delete | No    | Yes        | No   | 200, 204, 404
```

---

## 5. Path Parameters

Path parameters are **variable segments embedded in the URL path**.

### Syntax

```python
@app.get("/books/{book_title}")
async def get_book(book_title: str):
    ...
```

The `{book_title}` placeholder in the route string tells FastAPI:
- Extract this segment from the URL
- Inject it into the function as `book_title`
- Validate its type (here `str`)

### URL Examples

```
GET /books/Title%20One    →  book_title = "Title One"
GET /books/science        →  book_title = "science"
```

`%20` is URL-encoding for a space character.

### Type Validation

FastAPI uses the Python type hint to validate and convert automatically:

```python
@app.get("/items/{item_id}")
async def get_item(item_id: int):   # FastAPI rejects non-integer values with 422
    ...
```

### CRITICAL: Static vs Dynamic Route Ordering

FastAPI matches routes **top-to-bottom** in the order they were registered.

```python
# CORRECT — static route first
@app.get("/books/featured")      # matches /books/featured exactly
async def get_featured(): ...

@app.get("/books/{book_title}")  # matches everything else
async def get_book(book_title: str): ...


# WRONG — dynamic route registered first will eat /books/featured
@app.get("/books/{book_title}")  # "featured" would be captured here!
async def get_book(book_title: str): ...

@app.get("/books/featured")      # NEVER reached
async def get_featured(): ...
```

---

## 6. Query Parameters

Query parameters appear **after `?` in the URL** as `key=value` pairs, separated by `&`.

### Syntax

Any function parameter that is **not** a path parameter and **not** declared as `Body()` is automatically treated as a query parameter.

```python
@app.get("/books/")
async def get_books_by_category(category: str):
    ...
```

```
GET /books/?category=math
             ^^^^^^^^^^ query parameter
```

### Optional vs Required

```python
# Required — no default, client MUST provide it
async def search(category: str): ...

# Optional — has a default value
async def search(category: str = "all"): ...

# Optional nullable
from typing import Optional
async def search(category: Optional[str] = None): ...
```

### Multiple Query Parameters

```python
@app.get("/books/{author}/")
async def filter(author: str, category: str, limit: int = 10):
    # author   → path parameter
    # category → query parameter (required)
    # limit    → query parameter (optional, default 10)
    ...
```

```
GET /books/Author%20Two/?category=math&limit=5
```

### Query vs Path — When to Use Which

| Use path param when... | Use query param when... |
|---|---|
| The param **identifies** the resource | The param **filters or modifies** the response |
| `/users/42` | `/users?role=admin` |
| The param is always required | The param is optional |
| REST convention expects it in URL | You have many optional filters |

---

## 7. Request Body (`Body()`)

The request body carries **structured data** sent by the client, typically JSON.

### Why Bodies Exist

GET requests have no body — all data is in the URL. For POST/PUT/PATCH you need to send potentially large, structured data (a whole user object, a document, etc.) which doesn't fit cleanly in a URL.

### Using `Body()` with Raw Dicts

```python
from fastapi import Body

@app.post("/books/create_book")
async def create_book(new_book: dict = Body()):
    BOOKS.append(new_book)
```

FastAPI reads the JSON body and parses it into a Python `dict`.

### How to Send a Body (via Swagger UI `/docs`)

1. Go to `http://127.0.0.1:8000/docs`
2. Click the POST endpoint → "Try it out"
3. Paste JSON in the request body field:
   ```json
   {
       "title": "Title Seven",
       "author": "Author Seven",
       "category": "biology"
   }
   ```
4. Click "Execute"

### Using Pydantic Models (Recommended for Production)

Raw `dict` works but you lose validation and documentation. Use **Pydantic models** instead:

```python
from pydantic import BaseModel

class Book(BaseModel):
    title: str
    author: str
    category: str

@app.post("/books/create_book", status_code=201)
async def create_book(new_book: Book):   # No Body() needed — type hint is enough
    BOOKS.append(new_book.model_dump())
    return new_book
```

Benefits of Pydantic models:
- FastAPI validates the incoming JSON against the schema automatically
- Returns a clear `422 Unprocessable Entity` if data is invalid
- The model appears in the `/docs` UI as a schema
- You get IDE autocompletion on the object's fields

---

## 8. Combining Path, Query, and Body

FastAPI identifies each parameter by where it comes from:

```python
@app.put("/books/{book_id}")
async def update_book(
    book_id: int,               # PATH   — in the URL segment
    category: str = "fiction",  # QUERY  — after "?" in URL
    updated_book: dict = Body() # BODY   — in the JSON request body
):
    ...
```

```
PUT /books/42?category=sci-fi
Content-Type: application/json

{"title": "Dune", "author": "Frank Herbert", "category": "sci-fi"}
```

FastAPI resolves each argument automatically based on:
1. Is it in the path template? → **Path parameter**
2. Is it annotated with `Body()`? → **Request body**
3. Everything else → **Query parameter**

---

## 9. Status Codes

HTTP status codes tell the client what happened.

| Range | Meaning | Examples |
|---|---|---|
| 2xx | Success | 200 OK, 201 Created, 204 No Content |
| 3xx | Redirection | 301 Moved Permanently |
| 4xx | Client error | 400 Bad Request, 404 Not Found, 422 Unprocessable Entity |
| 5xx | Server error | 500 Internal Server Error |

### Setting Status Codes in FastAPI

```python
@app.post("/books/create_book", status_code=201)
async def create_book(...): ...
```

FastAPI defaults to `200` if you don't specify. FastAPI automatically returns `422` when request validation fails (wrong types, missing required fields).

---

## 10. Auto-Generated Docs (Swagger & ReDoc)

FastAPI generates interactive API documentation automatically from your code — no extra work needed.

### Swagger UI — `/docs`

```
http://127.0.0.1:8000/docs
```

- Lists all endpoints grouped by tags
- Shows request parameters, body schema, response schema
- Has a "Try it out" button — sends real HTTP requests from the browser
- Powered by the OpenAPI 3.x spec generated at `/openapi.json`

### ReDoc — `/redoc`

```
http://127.0.0.1:8000/redoc
```

- Read-only, cleaner layout
- Better for sharing API documentation with consumers

### How It Works

At startup FastAPI introspects every registered route:
- Function parameter names + type hints → parameter schemas
- Pydantic models → JSON Schema objects
- Docstrings → operation descriptions
- `status_code`, `tags`, `summary` → OpenAPI fields

Everything is assembled into an OpenAPI JSON document served at `/openapi.json`. The Swagger UI JavaScript reads this and renders the interactive page.

---

## 11. How to Run: Uvicorn — What It Is and Why

### 11.1 The Problem Uvicorn Solves

Traditional Python web servers (like Gunicorn's default `sync` worker) run synchronously — one request at a time per worker process. FastAPI is built on **async/await** which can handle thousands of concurrent connections in a single process — but only if the server understands the ASGI protocol.

**WSGI** (old, sync): Django, Flask
**ASGI** (new, async): FastAPI, Starlette, Django Channels

Uvicorn is an **ASGI server** — it bridges the gap between the network and your async Python application.

### 11.2 What Uvicorn Does

```
Internet
  → TCP connections
    → Uvicorn (HTTP/1.1 parsing, HTTP/2 optional, WebSocket upgrade)
      → ASGI interface: scope, receive, send
        → Your FastAPI app
```

Specifically Uvicorn:
1. Listens on a TCP socket (default `0.0.0.0:8000`)
2. Parses raw HTTP bytes into structured `scope` dicts
3. Calls your app's `async def __call__(scope, receive, send)`
4. Serializes response data back to HTTP bytes and sends them

Uvicorn is built on `uvloop` (a fast event loop) and `httptools` (a fast HTTP parser), both written in C — which is why FastAPI benchmarks are so competitive.

### 11.3 Running the App

**Basic (production-like):**
```bash
uvicorn main:app
```

- `main` → the Python module (`main.py`)
- `app` → the FastAPI instance inside that module

**Development (with auto-reload):**
```bash
uvicorn main:app --reload
```

`--reload` watches your source files for changes and restarts the server automatically. **Never use `--reload` in production** — it adds overhead and is not safe.

**Common flags:**

| Flag | Default | Description |
|---|---|---|
| `--host` | `127.0.0.1` | Bind to this IP. Use `0.0.0.0` to accept external connections |
| `--port` | `8000` | Port to listen on |
| `--reload` | off | Auto-restart on code changes (dev only) |
| `--workers` | 1 | Number of worker processes (don't combine with `--reload`) |
| `--log-level` | `info` | Log verbosity: `debug`, `info`, `warning`, `error` |

**Examples:**
```bash
# Expose to local network on port 8080
uvicorn main:app --host 0.0.0.0 --port 8080

# 4 workers for production (use with a process manager like systemd)
uvicorn main:app --workers 4

# Debug logging
uvicorn main:app --reload --log-level debug
```

### 11.4 Why Not Just `python main.py`?

You could add this to `main.py`:
```python
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", reload=True)
```

But the `uvicorn main:app --reload` CLI command is preferred because:
- The CLI is the standard deployment pattern
- It separates server config from app code
- Production tooling (Docker, systemd, Kubernetes) expects it

### 11.5 Uvicorn vs Gunicorn

In production with multiple CPU cores you'd use **Gunicorn** to manage multiple Uvicorn worker processes:

```bash
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker
```

- Gunicorn = process manager (handles worker crashes, restarts, signals)
- Uvicorn worker = ASGI handler within each process

For development and single-server deployments, plain Uvicorn is sufficient.

---

## 12. Mental Model: Full Request Lifecycle

```
curl "http://127.0.0.1:8000/books/Title%20One"

1. TCP connection established with Uvicorn
2. Uvicorn parses HTTP:
       GET /books/Title%20One HTTP/1.1
3. Uvicorn calls:
       await app(scope, receive, send)
   scope = {
       "type": "http",
       "method": "GET",
       "path": "/books/Title%20One",
       "query_string": b"",
       ...
   }
4. FastAPI middleware runs (CORS, auth, logging if configured)
5. Router matches path "/books/{book_title}" → get_book_by_title
6. FastAPI extracts:
       book_title = "Title One"  (URL-decoded, type-checked as str)
7. FastAPI calls:
       result = await get_book_by_title(book_title="Title One")
8. Python executes the function, returns:
       {"title": "Title One", "author": "Author One", "category": "science"}
9. FastAPI serializes to JSON bytes
10. FastAPI calls send() with:
        HTTP/1.1 200 OK
        Content-Type: application/json
        ...
        {"title":"Title One","author":"Author One","category":"science"}
11. Uvicorn sends bytes over TCP
12. curl prints the response
```

---

*Study this file alongside `main.py`. Every code comment in `main.py` maps to a section here.*
