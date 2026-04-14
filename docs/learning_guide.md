# FastAPI Boilerplate — Complete Learning Guide

> **Who is this for?** Complete beginners who want to understand every feature, pattern, and
> library used in this project. Each section explains the *concept*, *why it exists*, *how it
> works*, and then shows *exactly where it is used in this project* alongside a standalone
> dummy example you can run in isolation.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Tech Stack & Dependencies](#2-tech-stack--dependencies)
3. [Project Structure](#3-project-structure)
4. [FastAPI — Creating the Application](#4-fastapi--creating-the-application)
5. [Lifespan — Startup & Shutdown Events](#5-lifespan--startup--shutdown-events)
6. [Routing — APIRouter, Prefixes & Tags](#6-routing--apirouter-prefixes--tags)
7. [HTTP Methods — GET, POST, PUT, DELETE](#7-http-methods--get-post-put-delete)
8. [Path Parameters](#8-path-parameters)
9. [Query Parameters](#9-query-parameters)
10. [Request Body](#10-request-body)
11. [Response Models & Status Codes](#11-response-models--status-codes)
12. [Dependency Injection — Depends()](#12-dependency-injection--depends)
13. [Annotated Types](#13-annotated-types)
14. [Pydantic — Data Validation](#14-pydantic--data-validation)
15. [Pydantic Settings — Environment Configuration](#15-pydantic-settings--environment-configuration)
16. [SQLAlchemy — ORM & Database Layer](#16-sqlalchemy--orm--database-layer)
17. [Domain Objects — Dataclasses](#17-domain-objects--dataclasses)
18. [Layered Architecture — Repository, Service, Router](#18-layered-architecture--repository-service-router)
19. [Abstract Base Classes — Repository Interfaces](#19-abstract-base-classes--repository-interfaces)
20. [JWT Authentication — python-jose](#20-jwt-authentication--python-jose)
21. [Password Hashing — passlib & bcrypt](#21-password-hashing--passlib--bcrypt)
22. [OAuth2 — Login Form & Bearer Token](#22-oauth2--login-form--bearer-token)
23. [Role-Based Access Control](#23-role-based-access-control)
24. [Error Handling — RFC 7807 & Exception Hierarchy](#24-error-handling--rfc-7807--exception-hierarchy)
25. [Middleware — CORS & Custom Middleware](#25-middleware--cors--custom-middleware)
26. [Structured Logging & Correlation IDs](#26-structured-logging--correlation-ids)
27. [Rate Limiting — slowapi](#27-rate-limiting--slowapi)
28. [Database Migrations — Alembic](#28-database-migrations--alembic)
29. [Testing — pytest, TestClient & Dependency Overrides](#29-testing--pytest-testclient--dependency-overrides)
30. [OpenAPI / Swagger UI](#30-openapi--swagger-ui)
31. [Complete API Reference](#31-complete-api-reference)

---

## 1. Project Overview

This project is a **production-grade Todo API** built with FastAPI. It allows users to:

- Register and log in (JWT-based authentication)
- Create, read, update and delete their own todos
- Admins can see and delete any todo

More importantly, the codebase is structured to teach you how to build **real-world** FastAPI
applications: not just quick scripts, but maintainable, testable, layered systems.

### What does "production-grade" mean here?

| Concern | Solution used |
|---|---|
| Auth | JWT bearer tokens, bcrypt password hashing |
| Validation | Pydantic models with field constraints |
| Error responses | RFC 7807 Problem Details (standard format) |
| Logging | Structured JSON logs with per-request correlation IDs |
| Rate limiting | slowapi (IP-based) |
| Database schema versioning | Alembic migrations |
| Testability | Dependency injection overrides + in-memory DB |
| Architecture | 3-layer (Router → Service → Repository) |

---

## 2. Tech Stack & Dependencies

All dependencies are declared in `pyproject.toml`.

```toml
dependencies = [
    "fastapi[standard]>=0.115.0",   # Web framework
    "sqlalchemy>=2.0.0",            # ORM
    "pydantic-settings>=2.0.0",     # Config from .env
    "python-jose[cryptography]>=3.3.0",  # JWT tokens
    "passlib[bcrypt]>=1.7.4",       # Password hashing
    "slowapi>=0.1.9",               # Rate limiting
    "alembic>=1.13.0",              # DB migrations
    "psycopg2-binary>=2.9.0",       # PostgreSQL driver
    "bcrypt<4.0.0",                 # Bcrypt algorithm
]
```

**Dev-only dependencies** (only needed when running tests):

```toml
[dependency-groups]
dev = [
    "pytest>=8.0.0",          # Test runner
    "pytest-asyncio>=0.23.0", # Async test support
    "httpx>=0.27.0",          # HTTP client used by TestClient
]
```

**Why `fastapi[standard]`?** The `[standard]` extra automatically installs `uvicorn` (the
ASGI server that runs the app) and `httpx` among others. Without it, you'd need to install
uvicorn separately.

### Installing & Running

```bash
# Install the uv package manager (if not already installed)
pip install uv

# Install all dependencies from the lockfile
uv sync --group dev

# Copy the example env file and fill in your values
cp .env.example .env

# Run the development server
uv run uvicorn TodoApp.main:app --reload
```

---

## 3. Project Structure

```
fastapi-boilerplate/
├── pyproject.toml            ← project metadata + ALL dependencies
├── uv.lock                   ← lockfile for reproducible installs
├── .env.example              ← copy to .env and fill in secrets
├── .python-version           ← pins Python 3.11
│
├── docs/                     ← documentation (you are reading this)
│
└── TodoApp/                  ← main application package
    ├── main.py               ← app factory: wires everything together
    ├── config.py             ← reads .env into a typed Settings object
    ├── database.py           ← SQLAlchemy engine + session factory
    ├── models.py             ← ORM models (database tables)
    ├── domain.py             ← shared plain-Python dataclasses (UserData, TodoData)
    ├── dependencies.py       ← ALL Depends() wiring in one place
    │
    ├── core/
    │   ├── security.py       ← JWT helpers + password hashing
    │   └── errors.py         ← custom exception classes + global error handlers
    │
    ├── middleware/
    │   └── logging.py        ← JSON logging + correlation ID middleware
    │
    ├── schemas/              ← Pydantic request/response models (HTTP boundary)
    │   ├── auth.py
    │   ├── todo.py
    │   └── user.py
    │
    ├── repositories/         ← database access layer
    │   ├── interfaces.py     ← abstract contracts (ABCs)
    │   ├── user_repository.py
    │   └── todo_repository.py
    │
    ├── services/             ← business logic layer
    │   ├── auth_service.py
    │   ├── todo_service.py
    │   └── user_service.py
    │
    ├── routers/              ← HTTP endpoint handlers
    │   ├── auth.py
    │   ├── todos.py
    │   ├── users.py
    │   └── admin.py
    │
    ├── alembic/              ← database migration system
    │   ├── env.py
    │   └── versions/
    │
    └── test/                 ← test suite
        ├── utils.py          ← fixtures + dependency overrides
        ├── test_auth.py
        ├── test_todos.py
        ├── test_users.py
        └── test_admin.py
```

**Key mental model:** Data flows like this on every request:

```
HTTP Request
    ↓
Router (parse HTTP, validate input via Pydantic)
    ↓
Service (run business rules, raise domain errors)
    ↓
Repository (query/mutate the database)
    ↓
Domain Object (plain dataclass returned up the chain)
    ↓
Router (serialize domain object into HTTP response via Pydantic)
    ↓
HTTP Response
```

---

## 4. FastAPI — Creating the Application

### What is FastAPI?

FastAPI is a modern Python web framework for building APIs. It is:

- **Fast to run**: built on Starlette (ASGI) and uses async Python
- **Fast to write**: fewer lines of code than Flask/Django for the same API
- **Automatic docs**: generates Swagger UI and ReDoc from your code
- **Type-safe**: uses Python type hints to validate everything automatically

### The `FastAPI()` constructor

`FastAPI()` creates your application object. Every configuration option you pass here applies
to the whole application.

```python
# Dummy example
from fastapi import FastAPI

app = FastAPI(
    title="My API",          # shown in Swagger UI header
    version="1.0.0",         # shown in Swagger UI
    description="Docs here", # shown in Swagger UI
    docs_url="/docs",        # where Swagger UI is served (None = disabled)
    redoc_url="/redoc",      # where ReDoc is served    (None = disabled)
)
```

### In this project — `TodoApp/main.py`

```python
app = FastAPI(
    title=settings.APP_NAME,        # "FastAPI Boilerplate" from .env
    version=settings.APP_VERSION,   # "1.0.0" from .env
    description="Production-grade FastAPI boilerplate ...",
    lifespan=lifespan,              # startup/shutdown hook (see section 5)

    # Hide docs in production — docs exposed only in dev/test
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
)
```

**Why hide docs in production?** The Swagger UI lets anyone browse and call your API
endpoints interactively. In production that is a security and discovery risk — so docs are
disabled when `ENVIRONMENT=production` in `.env`.

---

## 5. Lifespan — Startup & Shutdown Events

### What is a lifespan?

When your API server starts up, you may need to do things like:
- Set up logging
- Create database tables (dev only)
- Connect to external services

When it shuts down, you may need to:
- Close connections
- Flush buffers

FastAPI provides a **lifespan context manager** for this. Code before `yield` runs at startup;
code after `yield` runs at shutdown.

### Dummy example

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Server starting up...")   # runs once at startup
    yield                            # server is running here
    print("Server shutting down...") # runs once at shutdown

app = FastAPI(lifespan=lifespan)
```

### In this project — `TodoApp/main.py`

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging("DEBUG" if settings.DEBUG else "INFO")  # configure JSON logging
    Base.metadata.create_all(bind=engine)                 # create tables if missing (dev)
    yield
    # nothing to clean up — SQLAlchemy closes connections automatically
```

`Base.metadata.create_all(bind=engine)` inspects all registered ORM models (the `Base`
subclasses in `models.py`) and creates their tables in the database if they don't exist.
In production, you run Alembic migrations instead (see section 28).

---

## 6. Routing — APIRouter, Prefixes & Tags

### What is routing?

Routing maps an HTTP method + URL path to a Python function. When a `GET /todo/5` request
arrives, the router finds the matching function and calls it.

### `APIRouter` vs registering routes directly on `app`

You *could* define all routes directly on `app`, but that would put thousands of lines in
one file. `APIRouter` lets you group related routes in their own file and then `include` them.

```python
# Dummy example — products.py
from fastapi import APIRouter

router = APIRouter(
    prefix="/products",  # prepended to every route in this router
    tags=["products"],   # groups routes under "products" in Swagger UI
)

@router.get("/")           # actual path: GET /products/
def list_products(): ...

@router.get("/{id}")       # actual path: GET /products/{id}
def get_product(id: int): ...
```

```python
# main.py — register the router
from fastapi import FastAPI
from products import router as products_router

app = FastAPI()
app.include_router(products_router)
```

### In this project

**`TodoApp/routers/auth.py`**
```python
router = APIRouter(prefix="/auth", tags=["auth"])
# Routes: POST /auth/   and   POST /auth/token
```

**`TodoApp/routers/todos.py`**
```python
router = APIRouter(tags=["todos"])
# No prefix — routes: GET /   GET /todo/{id}   POST /todo   PUT /todo/{id}   DELETE /todo/{id}
```

**`TodoApp/routers/admin.py`**
```python
router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin)],  # EVERY route in this router requires admin role
)
# Routes: GET /admin/todo   DELETE /admin/todo/{id}
```

**`TodoApp/routers/users.py`**
```python
router = APIRouter(prefix="/user", tags=["user"])
# Routes: GET /user/   PUT /user/password   PUT /user/phonenumber/{phone_number}
```

**`TodoApp/main.py`** — registers all routers:
```python
app.include_router(auth.router)
app.include_router(todos.router)
app.include_router(admin.router)
app.include_router(users.router)
```

### Router-level dependencies

Notice `admin.py` uses `dependencies=[Depends(require_admin)]` on the router, not on individual
routes. This means **every single route** in that router automatically requires admin. You don't
have to repeat yourself on each function.

```python
# Dummy example — router-level dependency
router = APIRouter(
    prefix="/secret",
    dependencies=[Depends(verify_api_key)],  # applies to ALL routes below
)

@router.get("/data")    # automatically protected — no need to add Depends here
def get_secret_data(): ...
```

---

## 7. HTTP Methods — GET, POST, PUT, DELETE

### The four methods and what they mean

| Method | Meaning | Typical use |
|---|---|---|
| `GET` | Read data | Fetch a list or a single item |
| `POST` | Create data | Submit a form, create a new resource |
| `PUT` | Replace/Update data | Update an existing resource fully |
| `DELETE` | Remove data | Delete a resource |

### In this project

```python
# TodoApp/routers/todos.py

@router.get("/")                        # READ — list todos
@router.get("/todo/{todo_id}")          # READ — single todo

@router.post("/todo", status_code=201)  # CREATE — new todo, returns 201
@router.put("/todo/{todo_id}", status_code=204)    # UPDATE
@router.delete("/todo/{todo_id}", status_code=204) # DELETE
```

### Dummy example — a complete CRUD for books

```python
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/books", tags=["books"])

class BookIn(BaseModel):
    title: str
    author: str

@router.get("/")              # GET  /books/
def list_books(): ...

@router.get("/{book_id}")     # GET  /books/42
def get_book(book_id: int): ...

@router.post("/", status_code=201)   # POST /books/
def create_book(data: BookIn): ...

@router.put("/{book_id}", status_code=204)    # PUT  /books/42
def update_book(book_id: int, data: BookIn): ...

@router.delete("/{book_id}", status_code=204) # DELETE /books/42
def delete_book(book_id: int): ...
```

---

## 8. Path Parameters

### What are path parameters?

Path parameters are **variable parts** of the URL. In `/todo/5`, the `5` is a path parameter
named `todo_id`. FastAPI extracts it from the URL and passes it to your function.

### Type coercion

Declare the type in the function signature and FastAPI validates + converts automatically.
If someone sends `GET /todo/abc` and your parameter is `int`, FastAPI returns a 422 error.

```python
# Dummy example
@app.get("/items/{item_id}")
def get_item(item_id: int):  # FastAPI converts "5" → 5, rejects "abc"
    return {"id": item_id}
```

### `Path()` — adding extra validation

`Path()` allows you to add more constraints beyond just the type.

```python
from fastapi import Path

@app.get("/items/{item_id}")
def get_item(item_id: int = Path(gt=0, lt=1000)):
    # gt=0  → must be > 0  (no zero or negative IDs)
    # lt=1000 → must be < 1000
    return {"id": item_id}
```

### In this project — `TodoApp/routers/todos.py`

```python
from fastapi import Path

@router.get("/todo/{todo_id}", response_model=TodoResponse)
async def read_todo(
    user: CurrentUserDep,
    service: TodoServiceDep,
    todo_id: int = Path(gt=0),   # must be a positive integer
) -> TodoResponse:
    return service.get_one(todo_id, user["id"])
```

`Path(gt=0)` ensures someone cannot request `GET /todo/0` or `GET /todo/-1`. FastAPI returns
a 422 error before the function is even called.

---

## 9. Query Parameters

### What are query parameters?

Query parameters appear after `?` in the URL: `/items?page=2&size=10`. They are optional
filters or pagination controls.

### Declaring query parameters

Any function parameter that is **not** a path parameter and **not** a Pydantic model is
treated as a query parameter.

```python
# Dummy example
@app.get("/items")
def list_items(
    page: int = 1,       # GET /items          → page=1 (default)
    size: int = 10,      # GET /items?page=3   → page=3, size=10
    active: bool = True, # GET /items?active=false
):
    return {"page": page, "size": size, "active": active}
```

### In this project

This boilerplate does not heavily use query parameters (the todo list returns all todos for
the authenticated user without pagination). However you can see how path and body params are
the primary input channels. Adding pagination would be straightforward:

```python
# How you would add pagination to the todo list endpoint
@router.get("/")
async def read_all(
    user: CurrentUserDep,
    service: TodoServiceDep,
    skip: int = 0,     # query param: GET /?skip=10
    limit: int = 20,   # query param: GET /?limit=5
) -> list[TodoResponse]:
    return service.get_all(user["id"], skip=skip, limit=limit)
```

---

## 10. Request Body

### What is a request body?

For POST/PUT requests, the client sends data as JSON in the **body** of the HTTP request
(not in the URL). FastAPI reads this body and validates it against a **Pydantic model**.

### Declaring a request body

If a function parameter has a type that is a `BaseModel` subclass, FastAPI treats it as
the request body.

```python
# Dummy example
from pydantic import BaseModel
from fastapi import APIRouter

class ItemIn(BaseModel):
    name: str
    price: float
    in_stock: bool = True

@app.post("/items")
def create_item(data: ItemIn):   # FastAPI reads JSON body → validates → passes as ItemIn
    print(data.name)             # "Laptop"
    print(data.price)            # 999.99
    return {"created": True}
```

If the client sends `{"name": "Laptop", "price": "not-a-number"}`, FastAPI automatically
returns a 422 response without calling your function.

### In this project — `TodoApp/schemas/todo.py`

```python
class TodoRequest(BaseModel):
    title: str = Field(..., min_length=3, examples=["Buy groceries"])
    description: str = Field(..., min_length=3, max_length=100, examples=["Milk, eggs, bread"])
    priority: int = Field(..., gt=0, lt=6, examples=[3])   # 1–5 only
    complete: bool = Field(default=False, examples=[False])
```

Used in the router:
```python
@router.post("/todo", status_code=201)
async def create_todo(
    user: CurrentUserDep,
    service: TodoServiceDep,
    data: TodoRequest,        # ← FastAPI reads JSON body into this
) -> None:
    service.create(data, user["id"])
```

---

## 11. Response Models & Status Codes

### Response models

`response_model=` tells FastAPI what shape the response JSON should have. FastAPI:
1. Calls your function
2. Takes the return value
3. Serializes it using the Pydantic model
4. Filters out any extra fields not in the model (security benefit)

```python
# Dummy example
class UserPublic(BaseModel):
    id: int
    username: str
    # NOTE: no "password" field — it will be stripped from the response

@app.get("/users/{id}", response_model=UserPublic)
def get_user(id: int):
    # Even if you accidentally return {"id":1, "username":"alice", "password":"secret"}
    # the response will only contain {"id":1, "username":"alice"}
    return {"id": 1, "username": "alice", "password": "supersecret"}
```

### `from_attributes = True`

By default, Pydantic only reads from Python dictionaries. To read from ORM model instances
(SQLAlchemy rows or dataclasses), you enable `from_attributes`:

```python
# TodoApp/schemas/todo.py
class TodoResponse(BaseModel):
    id: int
    title: str
    description: str | None
    priority: int
    complete: bool
    owner_id: int

    model_config = {"from_attributes": True}  # ← allows reading from dataclasses/ORM rows
```

### Status codes

HTTP status codes tell the client what happened:

| Code | Meaning | When to use |
|---|---|---|
| `200 OK` | Default success | GET requests that return data |
| `201 Created` | Resource was created | POST that creates something |
| `204 No Content` | Success, no body | PUT/DELETE that return nothing |
| `401 Unauthorized` | Not logged in | Missing or invalid token |
| `403 Forbidden` | Logged in but not allowed | Correct token, wrong role |
| `404 Not Found` | Resource doesn't exist | Requested ID doesn't exist |
| `409 Conflict` | Duplicate data | Registering an existing username |
| `422 Unprocessable Entity` | Validation failed | Invalid request body |
| `429 Too Many Requests` | Rate limit exceeded | Too many requests per minute |
| `500 Internal Server Error` | Unhandled exception | Bug in your code |

### In this project

```python
# 201 — resource created, returns no body
@router.post("/todo", status_code=status.HTTP_201_CREATED)
async def create_todo(...) -> None: ...

# 204 — success, no body
@router.put("/todo/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_todo(...) -> None: ...

# 200 — default, returns data
@router.get("/", response_model=list[TodoResponse])
async def read_all(...) -> list[TodoResponse]: ...
```

**Why use `status.HTTP_201_CREATED` instead of just `201`?** The `status` module (from
Starlette) provides named constants. `status.HTTP_201_CREATED` is much more readable and
prevents typos compared to a magic number.

---

## 12. Dependency Injection — Depends()

### What is dependency injection?

Dependency injection (DI) is a pattern where instead of a function creating its own
dependencies (database connections, services, etc.), those dependencies are **provided
from outside**. FastAPI's `Depends()` is its DI system.

**Why does this matter?**
- **Testing**: swap the real database with a fake one without touching any route code
- **Decoupling**: routes don't know how a database session is created
- **Reuse**: the same dependency can be used across hundreds of routes

### How `Depends()` works

```python
# Dummy example
from fastapi import Depends, FastAPI

app = FastAPI()

def get_database():           # "provider" function
    db = connect_to_db()
    try:
        yield db              # yield → FastAPI manages cleanup
    finally:
        db.close()

@app.get("/data")
def read_data(db = Depends(get_database)):   # FastAPI calls get_database() for us
    return db.query(...)
```

FastAPI sees `Depends(get_database)`, calls `get_database()`, injects the result as `db`,
and runs `db.close()` after the response is sent (because of the `try/finally`).

### Generator dependencies (yield)

When a provider function uses `yield`, FastAPI:
1. Runs everything before `yield` → injects the value
2. Sends the HTTP response
3. Runs everything after `yield` (cleanup)

This is essential for database sessions: you want the session open during the request and
closed after.

### In this project — `TodoApp/dependencies.py`

All `Depends()` wiring lives in a single file. This is a deliberate architectural choice: if
you ever need to override a dependency for testing, there's only one place to look.

```python
# Database session — yields a SQLAlchemy session, closes it after the request
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

DbDep = Annotated[Session, Depends(get_db)]

# Repository — depends on the DB session
def get_todo_repository(db: DbDep) -> AbstractTodoRepository:
    return TodoRepository(db)

TodoRepoDep = Annotated[AbstractTodoRepository, Depends(get_todo_repository)]

# Service — depends on the repository
def get_todo_service(repo: TodoRepoDep) -> TodoService:
    return TodoService(repo)

TodoServiceDep = Annotated[TodoService, Depends(get_todo_service)]
```

**Dependency chain:** FastAPI resolves the whole chain automatically.
```
Request arrives
  → FastAPI calls get_db()        → provides Session
  → FastAPI calls get_todo_repository(db) → provides TodoRepository
  → FastAPI calls get_todo_service(repo)  → provides TodoService
  → Your route function runs with service already built
  → FastAPI closes db session
```

### Using a dependency in a route

```python
# TodoApp/routers/todos.py
@router.post("/todo", status_code=201)
async def create_todo(
    user: CurrentUserDep,    # injected by get_current_user
    service: TodoServiceDep, # injected by the chain above
    data: TodoRequest,       # from request body
) -> None:
    service.create(data, user["id"])
```

The route function has zero knowledge of SQLAlchemy, database URLs, or how a session is
created. It just receives a ready-to-use `TodoService`.

---

## 13. Annotated Types

### What are `Annotated` types?

`Annotated[X, metadata]` is a Python standard library feature that attaches extra information
to a type hint. FastAPI uses it as a shorthand for dependency declarations.

```python
from typing import Annotated
from fastapi import Depends

# Without Annotated — verbose
def route(db: Session = Depends(get_db)): ...

# With Annotated — define it once, reuse everywhere
DbDep = Annotated[Session, Depends(get_db)]

def route(db: DbDep): ...          # clean, no repetition
def another_route(db: DbDep): ...  # same thing
```

### In this project — `TodoApp/dependencies.py`

```python
DbDep         = Annotated[Session,                  Depends(get_db)]
CurrentUserDep = Annotated[dict,                    Depends(get_current_user)]
UserRepoDep    = Annotated[AbstractUserRepository,  Depends(get_user_repository)]
TodoRepoDep    = Annotated[AbstractTodoRepository,  Depends(get_todo_repository)]
AuthServiceDep = Annotated[AuthService,             Depends(get_auth_service)]
TodoServiceDep = Annotated[TodoService,             Depends(get_todo_service)]
UserServiceDep = Annotated[UserService,             Depends(get_user_service)]
```

These aliases are then used directly in route signatures:

```python
# Clean, readable route signatures
async def create_todo(user: CurrentUserDep, service: TodoServiceDep, data: TodoRequest):
```

---

## 14. Pydantic — Data Validation

### What is Pydantic?

Pydantic is a Python library for data validation using type hints. When you create a Pydantic
`BaseModel` subclass, Pydantic will:
- Parse incoming data (from JSON, dicts, etc.)
- Validate each field against its type and constraints
- Convert data types automatically (e.g., `"5"` → `5` for an `int` field)
- Raise clear errors for invalid data

FastAPI uses Pydantic for all request bodies and response models.

### `BaseModel` — defining a schema

```python
# Dummy example
from pydantic import BaseModel, Field, EmailStr

class UserCreate(BaseModel):
    username: str                   # required string
    email: EmailStr                 # validated email address
    age: int = 18                   # optional with default
    password: str = Field(
        ...,                        # ... means required (no default)
        min_length=8,               # at least 8 characters
        max_length=100,             # at most 100 characters
        examples=["MyPass123!"],    # shown in Swagger UI
    )
```

### `Field()` — adding constraints

`Field()` is Pydantic's way to add extra metadata and validation rules to a field.

| Argument | Meaning |
|---|---|
| `...` | Required field (no default) |
| `default=X` | Optional field with default value X |
| `min_length=N` | String must be at least N chars |
| `max_length=N` | String must be at most N chars |
| `gt=N` | Number must be greater than N |
| `lt=N` | Number must be less than N |
| `ge=N` | Number must be greater than or equal to N |
| `le=N` | Number must be less than or equal to N |
| `examples=[...]` | Shown in Swagger UI as example values |

### In this project — schemas

**`TodoApp/schemas/todo.py`**
```python
class TodoRequest(BaseModel):
    title: str = Field(..., min_length=3, examples=["Buy groceries"])
    description: str = Field(..., min_length=3, max_length=100, examples=["Milk, eggs, bread"])
    priority: int = Field(..., gt=0, lt=6, examples=[3])  # must be 1, 2, 3, 4, or 5
    complete: bool = Field(default=False, examples=[False])
```

**`TodoApp/schemas/auth.py`**
```python
class CreateUserRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, examples=["johndoe"])
    email: EmailStr = Field(..., examples=["john@example.com"])  # validates email format
    first_name: str = Field(..., min_length=1, examples=["John"])
    last_name: str = Field(..., min_length=1, examples=["Doe"])
    password: str = Field(..., min_length=8, examples=["securePass123"])
    role: str = Field(default="user", examples=["user"])
    phone_number: str = Field(default="", examples=["+1-555-555-5555"])
```

### `EmailStr`

`EmailStr` is a special Pydantic type that validates the value looks like a real email address
(`user@domain.com`). It is part of the `email-validator` package that comes with `fastapi[standard]`.

### `model_config = {"from_attributes": True}`

By default, Pydantic only builds models from dictionaries. When you return a SQLAlchemy ORM
object or a Python dataclass from a route, Pydantic would fail to serialize it.

`from_attributes = True` tells Pydantic to read attribute values (like `obj.title`) rather
than only dictionary keys.

```python
# TodoApp/schemas/todo.py
class TodoResponse(BaseModel):
    id: int
    title: str
    description: str | None
    priority: int
    complete: bool
    owner_id: int

    model_config = {"from_attributes": True}  # so we can return a TodoData dataclass directly
```

Without this, returning a `TodoData(id=1, title="Learn Python", ...)` would cause a
serialization error.

---

## 15. Pydantic Settings — Environment Configuration

### Why use environment variables?

Hard-coding secrets (database passwords, JWT keys) in source code is a security risk.
When you commit code to GitHub, those secrets become public. The solution is:
1. Store secrets in a `.env` file (never committed to git)
2. Read them at runtime from environment variables

### `pydantic-settings`

`pydantic-settings` extends Pydantic's validation to read values from environment variables
and `.env` files. You define a class, and it auto-populates from the environment.

### Dummy example

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Config(BaseSettings):
    DATABASE_URL: str                      # required — must be in .env or environment
    DEBUG: bool = False                    # optional with default
    MAX_CONNECTIONS: int = 10              # optional with default

    model_config = SettingsConfigDict(
        env_file=".env",           # where to look for the file
        case_sensitive=True,       # DATABASE_URL ≠ database_url
        extra="ignore",            # ignore unknown env vars (don't error)
    )

config = Config()
print(config.DATABASE_URL)  # reads from .env or environment
```

### `@lru_cache` — singleton pattern

```python
from functools import lru_cache

@lru_cache
def get_settings() -> Settings:
    return Settings()
```

`lru_cache` makes `get_settings()` a singleton: it reads `.env` only **once** (the first
call) and returns the same object on every subsequent call. This avoids re-reading the file
on every request.

### In this project — `TodoApp/config.py`

```python
class Settings(BaseSettings):
    APP_NAME: str = "FastAPI Boilerplate"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: Literal["development", "production", "test"] = "development"
    DEBUG: bool = False
    DATABASE_URL: str = "sqlite:///./todosapp.db"
    SECRET_KEY: str = "change-me-in-production-..."
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 20
    RATE_LIMIT_PER_MINUTE: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )

@lru_cache
def get_settings() -> Settings:
    return Settings()
```

### `.env.example` — what to put in your `.env`

```ini
APP_NAME=My Todo API
ENVIRONMENT=development
DEBUG=true
DATABASE_URL=sqlite:///./todosapp.db
SECRET_KEY=super-secret-key-change-me
ACCESS_TOKEN_EXPIRE_MINUTES=60
RATE_LIMIT_PER_MINUTE=100
```

---

## 16. SQLAlchemy — ORM & Database Layer

### What is an ORM?

ORM stands for Object-Relational Mapper. Without an ORM, you write raw SQL:
```sql
SELECT * FROM todos WHERE owner_id = 5
```

With SQLAlchemy, you write Python:
```python
db.query(Todos).filter(Todos.owner_id == 5).all()
```

The ORM translates Python code into SQL, handles connections, and maps database rows to
Python objects.

### Engine — the database connection

The `engine` is SQLAlchemy's connection manager. It holds the database URL and a pool of
connections.

```python
# Dummy example
from sqlalchemy import create_engine

# SQLite (file-based, good for development)
engine = create_engine("sqlite:///./myapp.db", connect_args={"check_same_thread": False})

# PostgreSQL (server-based, for production)
engine = create_engine("postgresql://user:password@localhost:5432/mydb")
```

`check_same_thread=False` is a SQLite-only setting. SQLite's default is to only allow
use from the thread that created the connection. FastAPI may handle a request across
multiple threads/async tasks, so we disable this restriction.

`pool_pre_ping=True` sends a test query before using a connection from the pool. This
detects stale/dropped connections and recycles them, preventing mysterious "connection lost"
errors after idle periods.

### In this project — `TodoApp/database.py`

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from .config import get_settings

settings = get_settings()

_connect_args = (
    {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
)

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=_connect_args,
    pool_pre_ping=True,  # recycles stale connections
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass
```

**`sessionmaker`** creates a factory for database sessions. Each request gets its own
session (connection to the database).

**`autocommit=False`** means you must explicitly call `db.commit()` to save changes.
This prevents accidental partial saves.

**`autoflush=False`** means SQLAlchemy won't automatically send pending changes to the
database before queries. More predictable behavior.

**`DeclarativeBase`** is the base class all your ORM models inherit from. It registers
them so Alembic can detect schema changes.

### ORM Models — `TodoApp/models.py`

ORM models define your database tables as Python classes.

```python
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from .database import Base

class Users(Base):
    __tablename__ = "users"  # the actual table name in the database

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False)
    username = Column(String, unique=True, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    role = Column(String, nullable=False, default="user")
    phone_number = Column(String, nullable=True)  # nullable — can be NULL in DB


class Todos(Base):
    __tablename__ = "todos"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    priority = Column(Integer, nullable=False)
    complete = Column(Boolean, default=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    #                                ^^^^^^^^^^^^^^^^^^
    #                                Foreign key → must match a users.id value
```

**Column types explained:**

| Column type | Python type | Notes |
|---|---|---|
| `Integer` | `int` | Whole numbers |
| `String` | `str` | Variable-length text |
| `Boolean` | `bool` | True/False |
| `ForeignKey("table.column")` | `int` | Points to another table's column |

**Column arguments:**

| Argument | Meaning |
|---|---|
| `primary_key=True` | This column is the unique row identifier |
| `index=True` | Create a database index for faster lookups |
| `unique=True` | No two rows can have the same value |
| `nullable=False` | Column is required (NOT NULL in SQL) |
| `nullable=True` | Column can be empty (NULL in SQL) |
| `default=X` | Default value when not provided |

### Querying the database

```python
# Dummy example of common SQLAlchemy queries

# Get by primary key (most efficient)
user = db.get(Users, 5)          # SELECT * FROM users WHERE id = 5

# Filter query
user = db.query(Users).filter(Users.username == "alice").first()

# Get all
todos = db.query(Todos).filter(Todos.owner_id == 5).all()

# Create
new_user = Users(username="alice", email="alice@example.com", ...)
db.add(new_user)
db.commit()
db.refresh(new_user)  # reload from DB to get the assigned id

# Update
user = db.get(Users, 5)
user.email = "newemail@example.com"
db.commit()

# Delete
todo = db.get(Todos, 10)
db.delete(todo)
db.commit()
```

---

## 17. Domain Objects — Dataclasses

### The problem they solve

When you query a SQLAlchemy ORM object, it is "attached" to a database session. Pass it
to another layer (e.g., a service function) and unexpected things can happen: lazy loading
fires more SQL queries, the session might be closed, etc.

The solution is to convert the ORM object into a **plain Python object** immediately after
reading from the database and work with that plain object everywhere else.

### Python `dataclass`

A `dataclass` is a plain Python class that holds data. It's like a struct. No ORM, no
framework, no magic.

```python
# Dummy example
from dataclasses import dataclass

@dataclass
class ProductData:
    id: int
    name: str
    price: float
    in_stock: bool

# Create an instance
p = ProductData(id=1, name="Laptop", price=999.99, in_stock=True)
print(p.name)     # "Laptop"
print(p.price)    # 999.99
```

### In this project — `TodoApp/domain.py`

```python
from dataclasses import dataclass

@dataclass
class UserData:
    id: int
    username: str
    email: str
    first_name: str
    last_name: str
    hashed_password: str
    is_active: bool
    role: str
    phone_number: str | None   # can be None if user has no phone number

@dataclass
class TodoData:
    id: int
    title: str
    description: str | None
    priority: int
    complete: bool
    owner_id: int
```

**`id = 0` convention:** When creating a new object to be persisted, `id=0` signals "not
saved yet". The repository sets the real ID after the database assigns it.

```python
# TodoApp/services/auth_service.py
self._repo.create(UserData(
    id=0,          # ← 0 means "DB hasn't assigned an ID yet"
    username=data.username,
    ...
))
```

### Why this matters — the architecture benefit

The service layer (`services/`) only imports from `domain.py` and `repositories/interfaces.py`.
It **never** imports SQLAlchemy. This means:

- You can swap PostgreSQL for MongoDB by writing a new repository implementation — the service
  code stays identical
- Services are easy to unit-test because there's no database to connect to
- No accidental lazy-loading bugs

---

## 18. Layered Architecture — Repository, Service, Router

This project follows a **3-layer architecture**. Understanding this is the most important
architectural concept in the codebase.

### The three layers

```
┌─────────────────────────────────────────────────────────────────────┐
│  ROUTER LAYER  (routers/)                                           │
│  Knows about: HTTP, Pydantic schemas, status codes                  │
│  Does: Parse request → call service → return HTTP response          │
│  Does NOT: contain business logic, import SQLAlchemy                │
└─────────────────────┬───────────────────────────────────────────────┘
                      │ calls
┌─────────────────────▼───────────────────────────────────────────────┐
│  SERVICE LAYER  (services/)                                         │
│  Knows about: domain objects, repository interfaces, business rules │
│  Does: Validate business rules → call repository → return data      │
│  Does NOT: know about HTTP, import SQLAlchemy, import Pydantic      │
└─────────────────────┬───────────────────────────────────────────────┘
                      │ calls
┌─────────────────────▼───────────────────────────────────────────────┐
│  REPOSITORY LAYER  (repositories/)                                  │
│  Knows about: SQLAlchemy, ORM models, database queries              │
│  Does: CRUD operations → convert ORM rows to domain objects         │
│  Does NOT: know about HTTP, business rules, or Pydantic schemas     │
└─────────────────────────────────────────────────────────────────────┘
```

### The flow for "Create a todo"

**Step 1 — Router** receives `POST /todo` with JSON body:
```python
# TodoApp/routers/todos.py
@router.post("/todo", status_code=201)
async def create_todo(user: CurrentUserDep, service: TodoServiceDep, data: TodoRequest):
    service.create(data, user["id"])   # delegate to service
    # no return needed → 201 No Content
```

**Step 2 — Service** applies business rules:
```python
# TodoApp/services/todo_service.py
def create(self, data: TodoRequest, owner_id: int) -> TodoData:
    return self._repo.create(TodoData(
        id=0,                       # placeholder
        title=data.title,
        description=data.description,
        priority=data.priority,
        complete=data.complete,
        owner_id=owner_id,
    ))
```
The service converts the Pydantic `TodoRequest` into a domain `TodoData` and calls the
repository. The service doesn't know about SQL; it just calls `create()` on the repository.

**Step 3 — Repository** executes the SQL:
```python
# TodoApp/repositories/todo_repository.py
def create(self, data: TodoData) -> TodoData:
    todo = Todos(           # ORM model
        title=data.title,
        description=data.description,
        priority=data.priority,
        complete=data.complete,
        owner_id=data.owner_id,
    )
    self._db.add(todo)
    self._db.commit()
    self._db.refresh(todo)
    return _to_data(todo)   # convert ORM row back to domain dataclass
```

### Why this structure?

**Testability:** You can test `TodoService` with a fake (in-memory) repository. No database
needed.

**Replaceability:** If you want to add Redis caching, you wrap the repository. The service
and router don't change.

**Readability:** Each file has one clear job. `todo_service.py` only has business logic.
`todo_repository.py` only has SQL queries.

---

## 19. Abstract Base Classes — Repository Interfaces

### What is an Abstract Base Class?

An Abstract Base Class (ABC) is a class that defines a **contract** — a set of methods
that any subclass MUST implement. Python raises an error if you try to instantiate a
class that doesn't implement all abstract methods.

```python
# Dummy example
from abc import ABC, abstractmethod

class AbstractAnimal(ABC):
    @abstractmethod
    def speak(self) -> str: ...   # every animal MUST implement this

class Dog(AbstractAnimal):
    def speak(self) -> str:
        return "Woof"

class Cat(AbstractAnimal):
    def speak(self) -> str:
        return "Meow"

# dog = AbstractAnimal()   # ← TypeError! Can't instantiate abstract class
dog = Dog()
print(dog.speak())  # "Woof"
```

### In this project — `TodoApp/repositories/interfaces.py`

```python
from abc import ABC, abstractmethod
from ..domain import TodoData, UserData

class AbstractTodoRepository(ABC):

    @abstractmethod
    def get_all_by_owner(self, owner_id: int) -> list[TodoData]: ...

    @abstractmethod
    def get_by_id(self, todo_id: int) -> TodoData | None: ...

    @abstractmethod
    def create(self, data: TodoData) -> TodoData: ...

    @abstractmethod
    def save(self, data: TodoData) -> TodoData: ...

    @abstractmethod
    def delete(self, data: TodoData) -> None: ...
```

This interface says: "Any repository that handles todos MUST have these five methods."

The concrete SQLAlchemy implementation fulfils this contract:

```python
# TodoApp/repositories/todo_repository.py
class TodoRepository(AbstractTodoRepository):  # inherits the contract

    def __init__(self, db: Session) -> None:
        self._db = db

    def get_all_by_owner(self, owner_id: int) -> list[TodoData]:
        rows = self._db.query(Todos).filter(Todos.owner_id == owner_id).all()
        return [_to_data(t) for t in rows]

    # ... all other methods implemented
```

### The key benefit: dependency inversion

The service layer declares it needs an `AbstractTodoRepository`:

```python
class TodoService:
    def __init__(self, repo: AbstractTodoRepository) -> None:  # abstract, not concrete!
        self._repo = repo
```

The service only knows the *interface*. It can work with:
- `TodoRepository` (SQLAlchemy + SQLite)
- `TodoRepository` (SQLAlchemy + PostgreSQL)
- `MongoTodoRepository` (MongoDB)
- `FakeTodoRepository` (in-memory list, for tests)

All of these implement the same `AbstractTodoRepository` contract.

### The `_to_data()` mapper

```python
# TodoApp/repositories/todo_repository.py

def _to_data(t: Todos) -> TodoData:
    """Convert a SQLAlchemy ORM row into a plain TodoData dataclass."""
    return TodoData(
        id=t.id,
        title=t.title,
        description=t.description,
        priority=t.priority,
        complete=t.complete,
        owner_id=t.owner_id,
    )
```

This function is private (underscore prefix) to the repository file. It is the only place
that "knows" the mapping between an ORM column name and a domain field name.

---

## 20. JWT Authentication — python-jose

### What is JWT?

JWT (JSON Web Token) is a compact, self-contained token for securely transmitting
information between parties. The token carries claims (like user ID and role) and is
cryptographically signed — no one can alter the payload without invalidating the signature.

### JWT structure

A JWT looks like this: `xxxxx.yyyyy.zzzzz`

- **Header** (`xxxxx`): algorithm used (`HS256`)
- **Payload** (`yyyyy`): the claims (data)
- **Signature** (`zzzzz`): HMAC-SHA256 of header + payload using your SECRET_KEY

```json
// Decoded payload from this project
{
  "sub": "johndoe",    // subject — the username
  "id": 42,            // our custom claim — user ID
  "role": "user",      // our custom claim — role
  "exp": 1713000000    // expiry — Unix timestamp
}
```

**Important:** The payload is only **base64-encoded**, not encrypted. Anyone can decode and
read it. Never put sensitive data (passwords, credit card numbers) in a JWT. The value is in
the **signature** — if someone alters the payload, the signature becomes invalid and the server
rejects the token.

### In this project — `TodoApp/core/security.py`

```python
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from passlib.context import CryptContext
from ..config import get_settings

settings = get_settings()

def create_access_token(subject: dict, expires_delta: timedelta | None = None) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return jwt.encode(
        {**subject, "exp": expire},   # merge the claims dict with the expiry
        settings.SECRET_KEY,           # sign with the secret key
        algorithm=settings.ALGORITHM,  # "HS256"
    )

def decode_access_token(token: str) -> dict:
    """Raises JWTError if token is expired, invalid, or tampered with."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
```

### Token creation (login)

```python
# TodoApp/services/auth_service.py
def login(self, username: str, password: str) -> Token:
    user = self._repo.get_by_username(username)
    if not user or not verify_password(password, user.hashed_password):
        raise UnauthorizedError("Incorrect username or password.")

    token = create_access_token({
        "sub": user.username,   # standard JWT claim: subject
        "id": user.id,          # custom claim: our user ID
        "role": user.role,      # custom claim: role for authorization
    })
    return Token(access_token=token)
```

### Token validation (every protected request)

```python
# TodoApp/dependencies.py
def get_current_user(token: Annotated[str, Depends(oauth2_bearer)]) -> dict:
    try:
        payload = decode_access_token(token)   # raises JWTError if invalid
    except JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials.")

    username = payload.get("sub")
    user_id = payload.get("id")
    user_role = payload.get("role")

    if username is None or user_id is None:
        raise HTTPException(status_code=401, detail="Could not validate credentials.")

    return {"username": username, "id": user_id, "user_role": user_role}
```

### The authentication flow

```
Client                                Server
  │                                      │
  │  POST /auth/token                    │
  │  { username, password }  ──────────► │
  │                                      │  1. Verify password
  │                                      │  2. Create JWT
  │  { access_token: "xxx.yyy.zzz" } ◄── │
  │                                      │
  │  GET /todo/                          │
  │  Authorization: Bearer xxx.yyy.zzz ► │
  │                                      │  3. Decode JWT
  │                                      │  4. Check expiry and signature
  │                                      │  5. Extract user ID, call service
  │  [ { id: 1, title: "..." }, ... ] ◄─ │
```

---

## 21. Password Hashing — passlib & bcrypt

### Why hash passwords?

**Never store plain-text passwords.** If your database is leaked, attackers immediately
have all user passwords. With hashing, they get unintelligible strings like
`$2b$12$T8HJq8VlR7PjHNpK9P1...` which take billions of years to brute-force with modern
hardware.

### How bcrypt works

Bcrypt is a one-way hashing algorithm:
1. Takes a plain-text password + a random salt
2. Runs a computationally expensive algorithm
3. Produces a fixed-length hash string

"One-way" means: you can verify a password matches a hash, but you **cannot** reverse a hash
back into the original password.

### In this project — `TodoApp/core/security.py`

```python
from passlib.context import CryptContext

_bcrypt = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return _bcrypt.hash(password)
    # "mysecret" → "$2b$12$T8HJq8VlR7PjHNpK9P1mfO..."

def verify_password(plain: str, hashed: str) -> bool:
    return _bcrypt.verify(plain, hashed)
    # verify_password("mysecret", "$2b$12$T8HJq8VlR...") → True
    # verify_password("wrong", "$2b$12$T8HJq8VlR...") → False
```

### Where each function is used

**`hash_password`** — called when registering a user:
```python
# TodoApp/services/auth_service.py
self._repo.create(UserData(
    ...
    hashed_password=hash_password(data.password),  # NEVER store plain password
    ...
))
```

**`verify_password`** — called when logging in and changing password:
```python
# TodoApp/services/auth_service.py
if not verify_password(password, user.hashed_password):
    raise UnauthorizedError("Incorrect username or password.")

# TodoApp/services/user_service.py
if not verify_password(data.password, user.hashed_password):
    raise UnauthorizedError("Current password is incorrect.")
```

---

## 22. OAuth2 — Login Form & Bearer Token

### `OAuth2PasswordRequestForm`

This is a FastAPI class that reads the request body as a form (not JSON) with two fields:
`username` and `password`. This is the standard OAuth2 "password flow" login format.

```python
# TodoApp/routers/auth.py
from fastapi.security import OAuth2PasswordRequestForm
from typing import Annotated

@router.post("/token", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    service: AuthServiceDep,
) -> Token:
    return service.login(form_data.username, form_data.password)
```

The client must send `application/x-www-form-urlencoded` (form data), not JSON:
```
POST /auth/token
Content-Type: application/x-www-form-urlencoded

username=johndoe&password=secret123
```

Swagger UI renders this as a proper login form automatically.

### `OAuth2PasswordBearer`

This tells FastAPI to look for a token in the `Authorization: Bearer <token>` request header.
It also tells Swagger UI where to go to get a token (the `tokenUrl`).

```python
# TodoApp/dependencies.py
from fastapi.security import OAuth2PasswordBearer

oauth2_bearer = OAuth2PasswordBearer(tokenUrl="/auth/token")
```

When a protected route is called:
1. FastAPI looks for `Authorization: Bearer <token>` in the request headers
2. Extracts the token string
3. Passes it to `get_current_user()` via `Depends(oauth2_bearer)`

If no token is present, FastAPI returns 401 automatically.

---

## 23. Role-Based Access Control

### What is RBAC?

Role-Based Access Control restricts what users can do based on their **role**. In this
project, roles are `"user"` (default) and `"admin"`.

Regular users can only manage their own todos. Admins can see and delete any todo.

### Implementation

The role is stored in the JWT token payload:
```python
# Token payload
{"sub": "alice", "id": 1, "role": "admin"}
```

And checked in a dependency:
```python
# TodoApp/dependencies.py
def require_admin(user: CurrentUserDep) -> None:
    """Raises 403 Forbidden if caller is not an admin."""
    if user.get("user_role") != "admin":
        raise ForbiddenError("Admin role required.")
```

The admin router applies this dependency to **all its routes** at the router level:
```python
# TodoApp/routers/admin.py
router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin)],   # ← applies to every route here
)

@router.get("/todo")       # automatically requires admin
@router.delete("/todo/{todo_id}")  # automatically requires admin
```

### Dummy example — multiple roles

```python
# Extending the pattern for more roles
def require_moderator(user: CurrentUserDep) -> None:
    if user.get("user_role") not in ("moderator", "admin"):
        raise ForbiddenError("Moderator role required.")

moderation_router = APIRouter(
    prefix="/moderation",
    dependencies=[Depends(require_moderator)],
)
```

---

## 24. Error Handling — RFC 7807 & Exception Hierarchy

### The problem with default error responses

By default, FastAPI returns errors like this:
```json
{"detail": "Not Found"}
```

This is not very useful for API clients. They need to know:
- What type of error occurred (a machine-readable URI)
- A human-readable title
- The HTTP status code
- A detailed description
- Which URL caused the problem

### RFC 7807 — Problem Details

RFC 7807 is an IETF standard for structured error responses. It defines a JSON format:

```json
{
  "type": "about:blank",
  "title": "Not Found",
  "status": 404,
  "detail": "Todo 99 not found.",
  "instance": "/todo/99"
}
```

`"type"` is normally a URI pointing to documentation about the error type. `"about:blank"`
is the RFC's placeholder for when no documentation page exists.

### Domain exception hierarchy — `TodoApp/core/errors.py`

Instead of raising generic `HTTPException` everywhere, this project defines a hierarchy
of domain exceptions:

```python
class AppError(Exception):
    """Base for all application errors — carries status code, title, detail."""
    def __init__(self, status_code: int, title: str, detail: str) -> None:
        self.status_code = status_code
        self.title = title
        self.detail = detail

class NotFoundError(AppError):
    def __init__(self, detail: str) -> None:
        super().__init__(404, "Not Found", detail)

class UnauthorizedError(AppError):
    def __init__(self, detail: str = "Authentication required.") -> None:
        super().__init__(401, "Unauthorized", detail)

class ForbiddenError(AppError):
    def __init__(self, detail: str = "Insufficient permissions.") -> None:
        super().__init__(403, "Forbidden", detail)

class ConflictError(AppError):
    def __init__(self, detail: str) -> None:
        super().__init__(409, "Conflict", detail)
```

Services raise these exceptions. The service has no HTTP knowledge — it just raises
`NotFoundError("Todo 5 not found.")` and the global handler converts it to a proper
HTTP response.

```python
# TodoApp/services/todo_service.py
def get_one(self, todo_id: int, owner_id: int) -> TodoData:
    todo = self._repo.get_by_id_and_owner(todo_id, owner_id)
    if not todo:
        raise NotFoundError(f"Todo {todo_id} not found.")  # no HTTP imports needed!
    return todo
```

### Global exception handlers — `register_error_handlers()`

```python
# TodoApp/core/errors.py
def register_error_handlers(app: FastAPI) -> None:

    @app.exception_handler(AppError)
    async def _app_error(request: Request, exc: AppError) -> JSONResponse:
        # Catches NotFoundError, UnauthorizedError, etc.
        return _problem(request, exc.status_code, exc.title, exc.detail)

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        # Catches FastAPI's own HTTPException (e.g., 405 Method Not Allowed)
        title = _STATUS_TITLES.get(exc.status_code, "Error")
        return _problem(request, exc.status_code, title, str(exc.detail))

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        # Catches Pydantic validation failures — adds per-field error detail
        errors = [
            {"field": ".".join(str(loc) for loc in e["loc"]), "message": e["msg"]}
            for e in exc.errors()
        ]
        return _problem(request, 422, "Validation Error",
                        "One or more fields failed validation.", {"errors": errors})

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        # Catch-all — logs the traceback, returns a generic 500
        logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
        return _problem(request, 500, "Internal Server Error", "An unexpected error occurred.")
```

### Validation error response example

When you send `POST /todo` with `priority: 10` (max is 5) and `title: "Hi"` (min length 3 works,
but say 1 char `"H"` doesn't), you get:

```json
{
  "type": "about:blank",
  "title": "Validation Error",
  "status": 422,
  "detail": "One or more fields failed validation.",
  "instance": "/todo",
  "errors": [
    {"field": "body.priority", "message": "Input should be less than 6"},
    {"field": "body.title",    "message": "String should have at least 3 characters"}
  ]
}
```

---

## 25. Middleware — CORS & Custom Middleware

### What is middleware?

Middleware sits between the HTTP server and your route handlers. Every request passes
through every registered middleware before reaching a route, and every response passes
back through middleware before being sent to the client.

```
Request → [Middleware 1] → [Middleware 2] → [Route Handler]
                                                    ↓ response
Response ← [Middleware 1] ← [Middleware 2] ←────────┘
```

Use middleware for things that apply to **every** request: logging, CORS headers,
authentication headers, rate limiting, etc.

### CORS — Cross-Origin Resource Sharing

Browsers refuse to make JavaScript fetch requests to a different domain than the page
was loaded from (security). CORS is a mechanism that lets your API explicitly allow
cross-origin requests.

```python
# TodoApp/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],         # allow any domain (tighten in production)
    allow_credentials=True,      # allow cookies and auth headers
    allow_methods=["*"],         # allow GET, POST, PUT, DELETE, etc.
    allow_headers=["*"],         # allow any request header
)
```

In production, replace `["*"]` with your actual frontend URL:
```python
allow_origins=["https://myapp.com", "https://www.myapp.com"]
```

### Custom middleware with `@app.middleware("http")`

For more control, you can write middleware as a plain async function:

```python
# Dummy example
from fastapi import Request, Response

@app.middleware("http")
async def add_process_time_header(request: Request, call_next) -> Response:
    start = time.time()
    response = await call_next(request)   # call the actual route handler
    duration = time.time() - start
    response.headers["X-Process-Time"] = str(duration)
    return response
```

### In this project — correlation ID middleware

```python
# TodoApp/middleware/logging.py

async def correlation_id_middleware(request: Request, call_next: Callable) -> Response:
    # 1. Read X-Request-ID from the incoming request, or generate a new UUID
    cid = request.headers.get("X-Request-ID") or str(uuid.uuid4())

    # 2. Store in a ContextVar (thread-safe, request-scoped)
    token = correlation_id_var.set(cid)

    start = time.perf_counter()
    try:
        response: Response = await call_next(request)   # handle the request
    finally:
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        _access_log.info("%s %s → %s (%.2f ms)",
                         request.method, request.url.path, response.status_code, elapsed_ms)
        correlation_id_var.reset(token)   # clean up after this request

    # 3. Echo the correlation ID back in the response header
    response.headers["X-Request-ID"] = cid
    return response
```

Registered in `main.py`:
```python
app.middleware("http")(correlation_id_middleware)
```

---

## 26. Structured Logging & Correlation IDs

### Why structured logging?

Unstructured logs are plain text:
```
2024-04-13 10:00:01 INFO Starting server
2024-04-13 10:00:05 ERROR Something went wrong
```

Hard to search, hard to aggregate, impossible to parse automatically.

**Structured logs** are JSON:
```json
{"timestamp": "2024-04-13T10:00:01", "level": "INFO", "logger": "access", "message": "GET /todo/ → 200 (12.34 ms)", "correlation_id": "a3f8b2c1-..."}
```

You can send these to a log aggregation service (Datadog, Grafana Loki, AWS CloudWatch)
and query them with SQL-like syntax:
```sql
SELECT * FROM logs WHERE level = 'ERROR' AND correlation_id = 'a3f8b2c1-...'
```

### The `_JSONFormatter`

```python
# TodoApp/middleware/logging.py
import json, logging

class _JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,        # "INFO", "ERROR", etc.
            "logger": record.name,             # "access", "TodoApp.services.auth_service", etc.
            "message": record.getMessage(),
            "correlation_id": correlation_id_var.get(""),  # from ContextVar
        }
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)  # full traceback
        return json.dumps(entry)
```

### `setup_logging()`

```python
def setup_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler()    # write to stdout
    handler.setFormatter(_JSONFormatter())
    root = logging.getLogger()
    root.handlers = [handler]            # replace default handler with JSON handler
    root.setLevel(level)
    # Silence noisy third-party loggers
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
```

Called at startup in `lifespan()`:
```python
setup_logging("DEBUG" if settings.DEBUG else "INFO")
```

### `ContextVar` — request-scoped state

Python's `contextvars.ContextVar` stores values that are **scoped to the current async
task** (i.e., the current request). It's the thread-safe way to pass data through async
code without passing it as function arguments.

```python
from contextvars import ContextVar

correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")

# In middleware — set the value for this request
token = correlation_id_var.set("abc-123")

# In a logger formatter (anywhere in the call stack during this request)
cid = correlation_id_var.get("")   # → "abc-123"

# After the request — clean up
correlation_id_var.reset(token)
```

### Correlation IDs — request tracing

A **correlation ID** is a unique ID attached to every request. Every log line produced
during that request includes the same ID. This lets you filter all logs for a single
problematic request:

```
User reports: "My request at 10:45 failed"

grep correlation_id logs.json | jq 'select(.correlation_id == "f7e2a1...")'
# → see every log line from that request, including the exact SQL query and stack trace
```

The client can provide their own ID via `X-Request-ID` header (useful for tracking
requests from the frontend), or the server generates a UUID automatically.

---

## 27. Rate Limiting — slowapi

### What is rate limiting?

Rate limiting prevents a single client from making too many requests in a short time.
Without it, a single bot could crash your server or consume all your database resources.

**Example limit:** 60 requests per minute per IP address.

### slowapi

`slowapi` is a rate limiting library for FastAPI/Starlette. It works by tracking request
counts keyed by some identifier (here, the client's IP address).

### In this project — `TodoApp/main.py`

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

# Create the limiter, keyed by client IP
limiter = Limiter(
    key_func=get_remote_address,                              # identify clients by IP
    default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"],  # e.g. "60/minute"
)

app.state.limiter = limiter  # attach to app so slowapi can find it

# Handle rate limit exceeded → returns 429 Too Many Requests
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

When a client exceeds 60 requests/minute, slowapi automatically returns:
```
HTTP 429 Too Many Requests
Retry-After: 60
```

### Dummy example — per-route limits

You can override the global limit for specific routes:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.get("/search")
@limiter.limit("10/minute")   # search is expensive — tighter limit
async def search(request: Request, q: str): ...

@app.get("/health")
@limiter.limit("1000/minute") # health check can be called frequently
async def health(): ...
```

---

## 28. Database Migrations — Alembic

### What is a database migration?

When you change your ORM models (add a column, rename a table, change a type), the
database schema doesn't update automatically. You need to write and run a **migration**:
a script that alters the database to match your new models.

Alembic is the standard migration tool for SQLAlchemy.

### Migration lifecycle

```
1. Change your ORM model (models.py)
2. Generate a migration script:
   alembic revision --autogenerate -m "add phone_number to users"
3. Review the generated script in alembic/versions/
4. Apply the migration:
   alembic upgrade head
```

### In this project — `TodoApp/alembic/env.py`

```python
# The most important parts of env.py

# Make the app importable
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _project_root)

# Import the app's database config and models
from TodoApp.config import get_settings
from TodoApp.database import Base
import TodoApp.models  # ← MUST import models so Alembic can see the schema

settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)  # use same URL as app
target_metadata = Base.metadata  # Alembic compares this against the actual DB schema
```

The `import TodoApp.models` line is critical — without it, Alembic doesn't know about
your ORM models and cannot detect changes.

### The actual migration that ran

```python
# TodoApp/alembic/versions/aeff25f89db0_add_phone_number_to_users.py

def upgrade() -> None:
    op.add_column("users", sa.Column("phone_number", sa.String(), nullable=True))

def downgrade() -> None:
    op.drop_column("users", "phone_number")
```

Every migration has `upgrade()` (apply the change) and `downgrade()` (undo it).

### Common Alembic commands

```bash
# Generate a new migration by comparing models vs DB
alembic revision --autogenerate -m "describe what changed"

# Apply all pending migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# See migration history
alembic history

# See current database version
alembic current
```

### Development vs production

In development, `Base.metadata.create_all(bind=engine)` (called in `lifespan()`) creates
tables automatically. In production, you always use Alembic:
- `create_all` doesn't track changes — it only creates missing tables
- Alembic tracks every schema change and applies them incrementally

---

## 29. Testing — pytest, TestClient & Dependency Overrides

### Why test?

Tests verify your code does what you expect. They catch bugs before users do and let you
refactor with confidence (if tests still pass, you didn't break anything).

### pytest basics

```bash
# Run all tests
pytest

# Run a specific file
pytest TodoApp/test/test_todos.py

# Run with verbose output
pytest -v

# Stop at first failure
pytest -x
```

### `TestClient` — HTTP testing without a running server

FastAPI provides `TestClient` (from Starlette, backed by `httpx`) which lets you make
HTTP requests to your app in tests — without starting a real server.

```python
# Dummy example
from fastapi.testclient import TestClient
from myapp.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
```

### Dependency overrides — replacing real dependencies in tests

The most powerful testing pattern in FastAPI. Instead of making the test use a real
PostgreSQL database, you swap it with an in-memory SQLite database.

```python
# TodoApp/test/utils.py

# Create a test-only database
SQLALCHEMY_DATABASE_URL = "sqlite:///./testdb.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False},
                        poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)   # create tables in the test DB

# Override get_db: return a session to the test database instead of the real one
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

# Override get_current_user: skip JWT validation, return a fake user dict
def override_get_current_user():
    return {"username": "testuser", "id": 1, "user_role": "admin"}
```

```python
# In each test file — install the overrides
from ..main import app
from ..dependencies import get_db, get_current_user

app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user
```

Now when `TestClient` calls a route that uses `Depends(get_db)`, FastAPI calls
`override_get_db()` instead. Routes work identically — they have no idea which DB
they're talking to.

### `StaticPool` — in-memory SQLite for tests

```python
from sqlalchemy.pool import StaticPool

engine = create_engine(
    "sqlite:///./testdb.db",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # reuse a single connection — required for in-memory SQLite
)
```

`StaticPool` reuses one connection across threads, which is needed for SQLite in tests
because in-memory databases disappear when the connection closes.

### pytest fixtures

A fixture is a function decorated with `@pytest.fixture` that sets up (and tears down)
test data. FastAPI test fixtures typically insert rows before the test and delete them after.

```python
# TodoApp/test/utils.py
@pytest.fixture
def test_todo():
    todo = Todos(title="Learn to code!", description="Need to learn everyday!",
                 priority=5, complete=False, owner_id=1)
    db = TestingSessionLocal()
    db.add(todo)
    db.commit()
    yield todo                          # test runs here
    with engine.connect() as conn:      # cleanup after test
        conn.execute(text("DELETE FROM todos;"))
        conn.commit()
```

```python
# In a test file — use the fixture
def test_read_all_authenticated(test_todo):   # fixture name as parameter → auto-injected
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()[0]["title"] == "Learn to code!"
```

### Integration test example

```python
# TodoApp/test/test_todos.py
def test_create_todo(test_todo):
    payload = {
        "title": "New Todo!",
        "description": "New todo description",
        "priority": 5,
        "complete": False,
    }
    response = client.post("/todo", json=payload)
    assert response.status_code == 201

    # Verify it was actually saved to the test database
    db = TestingSessionLocal()
    model = db.query(Todos).filter(Todos.id == 2).first()
    assert model.title == payload["title"]
```

### Unit test example

```python
# TodoApp/test/test_auth.py
def test_get_current_user_invalid_token():
    """Test that an invalid token raises 401."""
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(token="not.a.valid.token")
    assert exc_info.value.status_code == 401
```

### `pytest.ini_options` in `pyproject.toml`

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"          # run async tests automatically without extra decorator
testpaths = ["TodoApp/test"]   # only look for tests in this directory
pythonpath = ["."]             # add project root to Python path so imports work
```

---

## 30. OpenAPI / Swagger UI

### What is OpenAPI?

OpenAPI (formerly Swagger) is a standard specification format for describing REST APIs.
FastAPI generates the OpenAPI spec automatically from your route decorators and type hints.

### What you get for free

Navigate to `http://localhost:8000/docs` while the app is running. You'll see:

- **All endpoints** grouped by their `tags`
- **Request body schemas** generated from your Pydantic models
- **Response schemas** generated from your `response_model=`
- **A "Try it out" button** to call endpoints directly from the browser
- **Authentication UI** — click "Authorize" to enter a JWT token

Navigate to `http://localhost:8000/redoc` for the ReDoc alternative (better for reading,
not interactive).

### Enhancing the docs

You can add documentation hints to routes:

```python
@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",          # ← short title in Swagger UI
    responses={
        409: {"description": "Username or email already taken"},  # ← document error responses
        422: {"description": "Validation error"},
    },
)
async def create_user(data: CreateUserRequest, service: AuthServiceDep) -> None:
    service.register(data)
```

Field-level examples in Pydantic models also show up in Swagger UI:
```python
username: str = Field(..., examples=["johndoe"])  # ← shown as example value
```

### Disabling docs in production

```python
# TodoApp/main.py
app = FastAPI(
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
)
```

When these are `None`, the routes simply don't exist. The OpenAPI JSON schema at
`/openapi.json` is also hidden in production (FastAPI does this automatically when
both `docs_url` and `redoc_url` are `None`).

---

## 31. Complete API Reference

### Authentication Endpoints

| Method | Path | Auth | Body | Response |
|---|---|---|---|---|
| `POST` | `/auth/` | — | `CreateUserRequest` JSON | `201` (no body) |
| `POST` | `/auth/token` | — | `username` + `password` form | `200` `Token` |

**Register — `POST /auth/`**
```json
// Request body
{
  "username": "johndoe",
  "email": "john@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "password": "securePass123",
  "role": "user",
  "phone_number": "+1-555-555-5555"
}
// Response: 201 Created (empty body)
```

**Login — `POST /auth/token`**
```
// Request (form-encoded, NOT JSON)
Content-Type: application/x-www-form-urlencoded
username=johndoe&password=securePass123

// Response: 200 OK
{ "access_token": "eyJhbGciOiJIUzI1NiJ9...", "token_type": "bearer" }
```

---

### Todo Endpoints (requires JWT)

All todo endpoints require `Authorization: Bearer <token>` header.

| Method | Path | Body | Response |
|---|---|---|---|
| `GET` | `/` | — | `200` `[TodoResponse]` |
| `GET` | `/todo/{todo_id}` | — | `200` `TodoResponse` or `404` |
| `POST` | `/todo` | `TodoRequest` | `201` (no body) |
| `PUT` | `/todo/{todo_id}` | `TodoRequest` | `204` or `404` |
| `DELETE` | `/todo/{todo_id}` | — | `204` or `404` |

**`TodoRequest`** (request body for create/update)
```json
{
  "title": "Buy groceries",
  "description": "Milk, eggs, bread",
  "priority": 3,
  "complete": false
}
```

**`TodoResponse`** (returned by GET endpoints)
```json
{
  "id": 1,
  "title": "Buy groceries",
  "description": "Milk, eggs, bread",
  "priority": 3,
  "complete": false,
  "owner_id": 42
}
```

---

### User Endpoints (requires JWT)

| Method | Path | Body | Response |
|---|---|---|---|
| `GET` | `/user/` | — | `200` `UserResponse` |
| `PUT` | `/user/password` | `UserVerification` | `204` or `401` |
| `PUT` | `/user/phonenumber/{phone_number}` | — | `204` |

**`UserVerification`** (for password change)
```json
{
  "password": "currentPassword123",
  "new_password": "newPassword456"
}
```

**`UserResponse`**
```json
{
  "id": 42,
  "username": "johndoe",
  "email": "john@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "is_active": true,
  "role": "user",
  "phone_number": "+1-555-555-5555"
}
```

---

### Admin Endpoints (requires JWT + admin role)

| Method | Path | Response |
|---|---|---|
| `GET` | `/admin/todo` | `200` `[TodoResponse]` — all users' todos |
| `DELETE` | `/admin/todo/{todo_id}` | `204` or `404` |

---

### Health Check

| Method | Path | Response |
|---|---|---|
| `GET` | `/health` | `200` `{"status": "healthy", "version": "1.0.0"}` |

---

### Standard Error Response Shape

All errors follow RFC 7807:

```json
{
  "type": "about:blank",
  "title": "Not Found",
  "status": 404,
  "detail": "Todo 99 not found.",
  "instance": "/todo/99"
}
```

Validation errors include field-level details:
```json
{
  "type": "about:blank",
  "title": "Validation Error",
  "status": 422,
  "detail": "One or more fields failed validation.",
  "instance": "/todo",
  "errors": [
    {"field": "body.priority", "message": "Input should be less than 6"},
    {"field": "body.title",    "message": "String should have at least 3 characters"}
  ]
}
```

---

*Happy learning! Work through the sections in order — each one builds on the previous.*
