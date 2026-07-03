# Auth Module & Alembic Migrations

---

## What was added

A `src/auth/` module for user signup — username, email, first/last name, and a hashed password. No login/JWT yet, just account creation, following the same layered pattern as `src/books/` (see [crud_service_db.md](./crud_service_db.md)).

Alongside it, Alembic was introduced to manage the database schema going forward instead of `SQLModel.metadata.create_all`.

---

## Folder structure

```
src/auth/
├── __init__.py
├── model.py      # User table definition (SQLModel, table=True)
├── schema.py      # UserCreate / UserRead — request & response shapes
├── service.py     # UserService — DB queries and business rules
├── router.py      # /auth HTTP endpoints
└── utils.py       # password hashing helpers (bcrypt)
```

### `model.py`
The `User` table. Mirrors `books/model.py`'s pattern: UUID primary key, `created_at`/`updated_at` via `default_factory=utcnow`. `username` and `email` are `unique=True, index=True` so the DB itself rejects duplicates and lookups by email are fast. `hashed_password` stores the bcrypt hash — the plaintext password is never persisted.

### `schema.py`
Two Pydantic models, kept separate from the table model on purpose:
- `UserCreate` — what the client sends. `password` (min 8, max 72 chars — bcrypt's own hard limit) instead of `hashed_password`. `email` uses Pydantic's `EmailStr` for format validation.
- `UserRead` — what the API returns. Deliberately has no `hashed_password` field, so there's no way a hash ever leaks in a response, even by accident. (Contrast with `books`, which reuses the table model as its `response_model` — fine for books since there's nothing sensitive on it.)

### `utils.py`
Two functions, `hash_password` and `verify_password`, wrapping the `bcrypt` library directly:
```python
hash_password("secret")          # -> "$2b$12$..."
verify_password("secret", hash)  # -> True / False
```
`bcrypt.gensalt()` generates a fresh random salt per call, so hashing the same password twice gives two different hashes — this is what makes bcrypt resistant to rainbow-table attacks. `verify_password` isn't used yet (no login endpoint), but it's there for when JWT/login is added.

### `service.py`
`UserService.create()` checks `get_by_email()` first; if a user already exists it returns `None` instead of raising — same convention as `BookService`, which keeps HTTP concerns (404/409) out of the service and in the router.

### `router.py`
- `POST /auth/register` — create a user, returns `201` + `UserRead`, or `409` if the email is taken.
- `GET /auth/{user_id}` — fetch a user by id, `404` if missing.

Registered in `main.py` under the `auth` tag:
```python
app.include_router(auth_router, prefix="/api/v1")
```

---

## What changed elsewhere

- `src/main.py` no longer calls `init_db()` on startup (the `lifespan` hook that called it was removed). With Alembic in place, `create_all` and migrations would fight each other over who owns the schema — Alembic is now the single source of truth for tables, columns, and indexes.
- `src/db/main.py` still keeps `init_db()`/`SQLModel.metadata` — harmless to leave for quick local scripting, just no longer wired into the app lifecycle.

---

## What is Alembic, and why

Alembic is a migration tool for SQLAlchemy/SQLModel. A **migration** is a versioned, ordered script that changes the DB schema (create a table, add a column, add an index...). Each migration knows the one before it (`down_revision`), so the whole history forms a chain you can move forward (`upgrade`) or backward (`downgrade`).

**Why not just use `create_all()`?**
`create_all` only ever adds tables that don't exist yet — it can't alter an existing table (add a column, rename one, add a constraint) and it has no history. The moment you need to change a table that already has production data in it, you need migrations. It also means every environment (your laptop, a teammate's, staging, prod) can be brought to the exact same schema state by replaying the same scripts, instead of relying on whoever's `create_all` ran first.

---

## How it's wired up here

```
alembic/
├── env.py              # migration runtime config — reads DATABASE_URL, points at SQLModel.metadata
├── script.py.mako      # template used for every new migration file
└── versions/
    └── bc6d3dfac8a9_create_user_table.py
alembic.ini              # alembic CLI config (script location, logging)
```

Two things were customized in `alembic/env.py`:

1. **Database URL** — instead of the placeholder in `alembic.ini`, it pulls the real URL from the app's own `Config` (`src/config.py`), so migrations always target whatever `.env` points at:
   ```python
   config.set_main_option("sqlalchemy.url", Config.DATABASE_URL)
   ```
2. **Metadata target** — every model module is imported so its table registers on `SQLModel.metadata` before Alembic compares it to the live DB (`autogenerate` diffs against this):
   ```python
   from src.books import model as books_model  # noqa: F401
   from src.auth import model as auth_model  # noqa: F401
   target_metadata = SQLModel.metadata
   ```
   Any new module added under `src/` needs the same import added here, or Alembic won't see its table.

The generated template (`script.py.mako`) also has `import sqlmodel` added — SQLModel column types (like `AutoString`) show up in autogenerated migrations as `sqlmodel.sql.sqltypes.AutoString`, but Alembic's default template doesn't import `sqlmodel`, so every autogenerated file would otherwise fail with `NameError` until fixed by hand.

---

## Day-to-day commands

**Add/change a model**, then generate a migration for it:
```bash
uv run alembic revision --autogenerate -m "add is_active to user"
```
This diffs `target_metadata` against the live DB and writes a new file into `alembic/versions/`. Always read the generated file before applying it — autogenerate is good but not perfect (it won't catch some renames, check constraints, etc.).

**Apply migrations** (bring the DB up to the latest schema):
```bash
uv run alembic upgrade head
```

**Roll back one step:**
```bash
uv run alembic downgrade -1
```

**Check current DB version / history:**
```bash
uv run alembic current
uv run alembic history
```

Alembic tracks the applied version in a single-row table it creates itself: `alembic_version`.

---

## When to reach for a migration

- Adding a new table (like `user` here)
- Adding/removing/renaming a column
- Adding a constraint or index
- Any schema change that needs to happen on a database that already has real data in it

Not needed for query logic, service methods, or anything that doesn't touch table structure.
