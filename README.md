# fastapi-boilerplate

A production-shaped FastAPI backend boilerplate: async Postgres (SQLModel + SQLAlchemy),
JWT auth with access/refresh tokens, Alembic migrations, a clean layered architecture
(router → service → model), consistent error handling, middleware, and tests.

It ships with two example modules — **`books`** (a reference CRUD resource) and **`auth`**
(users + JWT) — that you can copy as the template for your own features.

> 📖 **Architecture & concepts:** [`docs/boilerplate_guide.md`](docs/boilerplate_guide.md)
> is a living, step-by-step guide to every file and pattern in this repo. This README is
> the "how do I run and use it" companion.

---

## Tech stack

| Concern | Choice |
|---|---|
| Web framework | FastAPI |
| ORM / models | SQLModel (SQLAlchemy + Pydantic) |
| Database | PostgreSQL via `asyncpg` (async) |
| NoSQL store | MongoDB via `motor` (async) — activity log |
| Migrations | Alembic |
| Auth | JWT (PyJWT) + bcrypt, access + refresh tokens |
| Package manager | [uv](https://docs.astral.sh/uv/) |
| Tests | pytest + pytest-asyncio + httpx `AsyncClient` |

---

## Prerequisites

- **Python 3.11+**
- **[uv](https://docs.astral.sh/uv/getting-started/installation/)** (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- A running **PostgreSQL** database
- *(Optional)* a **MongoDB** instance for the activity log — the app boots without it (`docker run -d -p 27017:27017 mongo:7`)

---

## Setup & run

```bash
# 1. Install dependencies (creates .venv automatically)
uv sync

# 2. Configure environment
cp .env.example .env
#    edit .env → set DATABASE_URL and a strong JWT_SECRET_KEY
#    generate a secret: python -c "import secrets; print(secrets.token_urlsafe(64))"

# 3. Create the database schema (runs Alembic migrations)
uv run alembic upgrade head

# 4. Run the dev server (auto-reload)
uv run uvicorn src.main:app --reload
```

The API is now live at **http://localhost:8000**.

- Interactive docs (Swagger UI): **http://localhost:8000/docs**
- Alternative docs (ReDoc): **http://localhost:8000/redoc**

### Environment variables (`.env`)

| Variable | Required | Default | Notes |
|---|---|---|---|
| `DATABASE_URL` | ✅ | — | `postgresql+asyncpg://user:pass@localhost:5432/dbname` |
| `JWT_SECRET_KEY` | ✅ | — | Long random string; different per environment, never commit prod |
| `JWT_ALGORITHM` | | `HS256` | |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | | `15` | Short-lived access token |
| `REFRESH_TOKEN_EXPIRE_DAYS` | | `7` | Long-lived refresh token |
| `CORS_ORIGINS` | | `["*"]` | Allowed browser origins (lock down in prod) |
| `ENVIRONMENT` | | `dev` | `prod` hides `/docs`, `/redoc`, `/openapi.json` |
| `MONGO_URL` | | `mongodb://localhost:27017` | Activity log store (optional) |
| `MONGO_DB` | | `bookstore` | Mongo database name |

---

## API overview

All routes are under the **`/api/v1`** prefix. Every `/books` route and the `/auth/me`
and `/auth/{id}` routes require a valid **access token** (`Authorization: Bearer <token>`).

| Method | Path | Auth | Body | Purpose |
|---|---|---|---|---|
| `POST` | `/auth/register` | — | JSON `UserCreate` | Create an account |
| `POST` | `/auth/login` | — | **form** `username`(=email) + `password` | Get access + refresh tokens (rate-limited 5/min) |
| `POST` | `/auth/refresh` | refresh token | JSON `{refresh_token}` | Swap for a fresh token pair (rate-limited 10/min) |
| `POST` | `/auth/logout` | refresh token | JSON `{refresh_token}` | Revoke the refresh token |
| `GET` | `/auth/me` | access token | — | The current user |
| `GET` | `/auth/{user_id}` | **admin** | — | Fetch a user by id (requires `is_admin`) |
| `GET` | `/books` | access token | — | List books (paginated/filtered/sorted) |
| `GET` | `/books/{book_id}` | access token | — | One book |
| `POST` | `/books` | access token | JSON `BookCreate` | Create a book |
| `PUT` | `/books/{book_id}` | access token | JSON `BookUpdate` | Update a book |
| `DELETE` | `/books/{book_id}` | access token | — | Delete a book |
| `GET` | `/activity` | **admin** | — | Audit feed from MongoDB (login / book events) |

Every error comes back in one consistent shape:
```json
{ "error": { "code": "not_found", "message": "Book 3fa… not found", "request_id": "a1b2…" } }
```

---

## The typical flow (with curl)

Set a base URL for convenience:
```bash
BASE=http://localhost:8000/api/v1
```

### 1. Register (once)
```bash
curl -X POST $BASE/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "alice",
    "email": "alice@example.com",
    "first_name": "Al",
    "last_name": "Ice",
    "password": "supersecret123"
  }'
# → 201  { "id": "...", "username": "alice", "email": "alice@example.com", ... }
```
> Note: `username`/`email` are stored lowercased. `password` must not contain the username.

### 2. Log in → get tokens
```bash
curl -X POST $BASE/auth/login \
  -d "username=alice@example.com&password=supersecret123"
# → 200  { "access_token": "eyJ...", "refresh_token": "eyJ...", "token_type": "bearer" }
```
> `login` uses the OAuth2 password **form** (not JSON): put the email in the `username` field.

Grab the access token into a variable:
```bash
ACCESS="eyJ..."      # paste the access_token from above
REFRESH="eyJ..."     # paste the refresh_token from above
```

### 3. Call protected endpoints
```bash
# Who am I?
curl $BASE/auth/me -H "Authorization: Bearer $ACCESS"

# Create a book
curl -X POST $BASE/books \
  -H "Authorization: Bearer $ACCESS" \
  -H "Content-Type: application/json" \
  -d '{"title": "Clean Code", "author": "Robert Martin", "year": 2008, "price": 30.5}'
# → 201  { "id": "...", "title": "Clean Code", ... }

# List books (see pagination/filtering below)
curl "$BASE/books" -H "Authorization: Bearer $ACCESS"
```
No token / expired token → **401** in the standard error shape.

### 4. Access token expired? Refresh it
```bash
curl -X POST $BASE/auth/refresh \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\": \"$REFRESH\"}"
# → 200  a NEW access_token AND a NEW refresh_token (the old refresh token is now dead)
```
Refresh tokens are **single-use** (rotation): each refresh invalidates the old one. A
typical client keeps the access token in memory and, on a `401`, calls `/auth/refresh`,
stores the new pair, and retries the original request.

### 5. Log out
```bash
curl -X POST $BASE/auth/logout \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\": \"$REFRESH\"}"
# → 204  (the refresh token can no longer mint new access tokens)
```

### Or just use Swagger UI
Open **http://localhost:8000/docs**, click **Authorize**, enter the email as *username*
and the password. Swagger logs in via `/auth/login` and attaches the access token to
every request automatically.

---

## Listing books: pagination, filtering, sorting

`GET /books` returns a paginated envelope and accepts query params:

| Param | Default | Notes |
|---|---|---|
| `limit` | `20` | 1–100 |
| `offset` | `0` | items to skip |
| `sort_by` | `created_at` | one of: `created_at`, `title`, `author`, `year`, `price` |
| `order` | `desc` | `asc` or `desc` |
| `author` | — | case-insensitive substring filter |

```bash
curl "$BASE/books?author=martin&limit=2&sort_by=year&order=asc" \
  -H "Authorization: Bearer $ACCESS"
```
```json
{ "items": [ { "...": "..." } ], "total": 3, "limit": 2, "offset": 0 }
```

---

## Running tests

```bash
uv sync --group dev     # first time: installs pytest, pytest-asyncio, httpx, aiosqlite
uv run pytest           # run everything
uv run pytest -q        # quieter output
uv run pytest tests/test_auth.py -v   # a single file, verbose
```

Tests run **fully in-process** — no server and no Postgres needed. They drive the ASGI app
via `httpx.AsyncClient` and use FastAPI's `dependency_overrides` to swap in an in-memory
SQLite database and a fake authenticated user. See [`tests/conftest.py`](tests/conftest.py).

---

## Database migrations (Alembic)

Alembic is the single source of truth for the schema (the app does **not** auto-create tables).

```bash
# After changing a model, generate a migration (always read the generated file!)
uv run alembic revision --autogenerate -m "add is_active to user"

uv run alembic upgrade head     # apply migrations
uv run alembic downgrade -1     # roll back one
uv run alembic current          # show current DB revision
uv run alembic history          # show the migration chain
```

> Any new module under `src/` must be imported in `alembic/env.py`, or Alembic won't see
> its table. Details in [`docs/boilerplate_guide.md`](docs/boilerplate_guide.md) §10.

---

## Project structure

```
src/
├── config.py          # typed settings from .env
├── main.py            # app + middleware + CORS + lifespan + error handlers
├── schemas.py         # shared base model, Page[T], error shape
├── dependencies.py    # shared deps (pagination params)
├── exceptions.py      # custom errors + consistent handlers
├── middleware.py      # request id + timing
├── logging_config.py  # structured JSON logging
├── ratelimit.py       # slowapi limiter
├── db/main.py         # async Postgres engine, session, get_session()
├── db/mongo.py        # async MongoDB client (activity log)
├── books/             # example CRUD module (model / schema / service / router)
├── auth/              # users + JWT (model / schema / utils / service / dependencies / router)
└── activity/          # MongoDB activity log (schema / service / router)
alembic/               # migration env + versioned scripts
scripts/               # seed_books.py, make_admin.py
tests/                 # pytest suite (AsyncClient + dependency_overrides)
```

Each file's purpose, the pattern it implements, and how it's used are documented
section-by-section in **[`docs/boilerplate_guide.md`](docs/boilerplate_guide.md)**.
