# FastAPI Boilerplate

Production-grade FastAPI template with layered architecture, JWT auth, rate limiting, structured logging, and PostgreSQL support. Clone and rename to start any new project.

---

## Architecture

```
TodoApp/
├── main.py              # App factory — middleware, routers, lifespan
├── config.py            # Pydantic Settings (reads from .env)
├── database.py          # SQLAlchemy engine + session (SQLite / PostgreSQL)
├── models.py            # ORM models
├── dependencies.py      # FastAPI Depends() wiring (single source of truth)
│
├── core/
│   ├── security.py      # JWT encode/decode, bcrypt hash/verify
│   └── errors.py        # RFC 7807 problem-details + AppError hierarchy
│
├── middleware/
│   └── logging.py       # Structured JSON logs + X-Request-ID correlation
│
├── schemas/             # Pydantic request/response models
│   ├── auth.py
│   ├── todo.py
│   └── user.py
│
├── repositories/        # Data-access layer (SQLAlchemy queries only)
│   ├── user_repository.py
│   └── todo_repository.py
│
├── services/            # Business logic (no HTTP, no SQLAlchemy)
│   ├── auth_service.py
│   ├── todo_service.py
│   └── user_service.py
│
├── routers/             # Thin HTTP handlers — validate → delegate → return
│   ├── auth.py          # POST /auth/, POST /auth/token
│   ├── todos.py         # CRUD /todo
│   ├── admin.py         # GET/DELETE /admin/todo
│   └── users.py         # GET/PUT /user
│
├── alembic/             # Database migrations
│   └── versions/
└── test/
    ├── utils.py         # Shared fixtures + dependency overrides
    ├── test_auth.py
    ├── test_todos.py
    ├── test_admin.py
    ├── test_users.py
    └── test_main.py
```

**Request flow:** `HTTP request → Middleware (correlation ID) → Router → Service → Repository → DB`

---

## Features

| Feature | Implementation |
|---|---|
| Layered architecture | router → service → repository |
| JWT auth + OAuth2 | `python-jose`, `OAuth2PasswordBearer` |
| Password hashing | `passlib[bcrypt]` |
| Rate limiting | `slowapi` (60 req/min per IP, configurable) |
| Structured JSON logging | Custom `logging.Formatter`, per-request `X-Request-ID` |
| RFC 7807 error responses | Global exception handlers in `core/errors.py` |
| OpenAPI docs | Auto-generated at `/docs` (hidden in production) |
| Database migrations | Alembic (auto-detects SQLite vs PostgreSQL) |
| PostgreSQL support | `psycopg2-binary` — swap URL in `.env` |

---

## Quick Start

### 1. Clone and configure

```bash
git clone <repo-url> my-new-app
cd my-new-app
cp .env.example .env
# Edit .env — at minimum change SECRET_KEY
```

### 2. Install dependencies

```bash
# With uv (recommended)
uv sync

# Or with pip
pip install -e ".[dev]"
```

### 3. Run (SQLite — zero config)

```bash
uv run fastapi dev TodoApp/main.py
```

Open **http://localhost:8000/docs** for the interactive API.

---

## PostgreSQL Setup

### Option A — Local PostgreSQL

```bash
# Start PostgreSQL (example with Docker)
docker run -d \
  --name postgres \
  -e POSTGRES_USER=todouser \
  -e POSTGRES_PASSWORD=todopass \
  -e POSTGRES_DB=todosapp \
  -p 5432:5432 \
  postgres:16-alpine
```

Update `.env`:

```env
DATABASE_URL=postgresql://todouser:todopass@localhost:5432/todosapp
```

Run migrations (creates all tables):

```bash
cd TodoApp
alembic upgrade head
```

Start the app:

```bash
uv run fastapi dev TodoApp/main.py
```

### Option B — Docker Compose (app + PostgreSQL together)

Create `docker-compose.yml` at the project root:

```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: todouser
      POSTGRES_PASSWORD: todopass
      POSTGRES_DB: todosapp
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://todouser:todopass@db:5432/todosapp
      SECRET_KEY: change-me
      ENVIRONMENT: production
    depends_on:
      - db

volumes:
  pgdata:
```

```bash
docker compose up
```

---

## Running Migrations

Migrations live in `TodoApp/alembic/versions/`. The `env.py` reads `DATABASE_URL` from your `.env` automatically.

```bash
# Apply all pending migrations
cd TodoApp && alembic upgrade head

# Roll back one migration
cd TodoApp && alembic downgrade -1

# Generate a new migration after changing models.py
cd TodoApp && alembic revision --autogenerate -m "add status column to todos"
```

---

## Running Tests

```bash
# All tests
uv run pytest

# With verbose output
uv run pytest -v

# Single file
uv run pytest TodoApp/test/test_todos.py -v
```

Tests use an **in-memory SQLite** database and override `get_db` / `get_current_user` via FastAPI's dependency injection system — no real database or tokens required.

---

## Configuration Reference

All settings are read from environment variables or a `.env` file.

| Variable | Default | Description |
|---|---|---|
| `APP_NAME` | `FastAPI Boilerplate` | Shown in OpenAPI docs |
| `APP_VERSION` | `1.0.0` | Shown in OpenAPI docs |
| `ENVIRONMENT` | `development` | `development` / `production` / `test` |
| `DEBUG` | `false` | Enables DEBUG log level |
| `DATABASE_URL` | `sqlite:///./todosapp.db` | SQLAlchemy connection string |
| `SECRET_KEY` | *(change this!)* | JWT signing key — `openssl rand -hex 32` |
| `ALGORITHM` | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `20` | Token lifetime |
| `RATE_LIMIT_PER_MINUTE` | `60` | Requests per IP per minute |

---

## API Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/health` | — | Health check |
| `POST` | `/auth/` | — | Register user |
| `POST` | `/auth/token` | — | Login → JWT token |
| `GET` | `/` | JWT | List my todos |
| `GET` | `/todo/{id}` | JWT | Get one todo |
| `POST` | `/todo` | JWT | Create todo |
| `PUT` | `/todo/{id}` | JWT | Update todo |
| `DELETE` | `/todo/{id}` | JWT | Delete todo |
| `GET` | `/user/` | JWT | My profile |
| `PUT` | `/user/password` | JWT | Change password |
| `PUT` | `/user/phonenumber/{n}` | JWT | Update phone |
| `GET` | `/admin/todo` | JWT + admin | All todos |
| `DELETE` | `/admin/todo/{id}` | JWT + admin | Delete any todo |

---

## Using This as a Template

When starting a new project:

1. **Copy** this repo and rename `TodoApp/` to your project name.
2. **Replace** `Todos` / `Users` models in `models.py` with your domain models.
3. **Add** repositories, services, and routers following the same pattern.
4. **Keep** `config.py`, `core/`, `middleware/`, and `dependencies.py` as-is — they are domain-agnostic.
5. **Generate** the initial migration: `alembic revision --autogenerate -m "initial schema"`.

The layered architecture means you can swap the database, change auth providers, or add a message queue without touching business logic.
