# FastAPI Backend Boilerplate — Living Guide

> A single, evolving reference for this repo. It has three parts:
> 1. **[The Structure Figure](#1-the-structure-figure)** — the project layout as a boilerplate: which file does what, its purpose, and its key snippet. *Keep this figure in sync as the project grows.*
> 2. **[Topics Index](#2-topics-index)** — every concept covered here and the snippet that demonstrates it.
> 3. **[Concept Deep-Dives](#3-concept-deep-dives)** — the "why" behind each piece, enough to start building FastAPI backends from scratch.
>
> The separate [`fastapi_mastery_roadmap.md`](./fastapi_mastery_roadmap.md) tracks the longer-term learning path; this guide is the hands-on companion.

---

## 1. The Structure Figure

**Legend** — each file is tagged by the layer it belongs to:

| | Layer | Responsibility |
|---|---|---|
| 🟢 | **Entry / Config** | Boot the app, load settings, open the DB engine |
| 🔵 | **Router (HTTP)** | Paths, status codes, request/response — *no SQL* |
| 🟣 | **Service (Business)** | Queries, commits, rules — *no HTTP* |
| 🟡 | **Model (Table)** | `SQLModel table=True` — maps a class to a DB table |
| 🟠 | **Schema (Contract)** | Pydantic request/response shapes — *not the table* |
| 🔴 | **Auth / Security** | Hashing, JWTs, the `get_current_user` guard |
| ⚫ | **Migrations** | Alembic — versioned schema history |

```text
fastapi-boilerplate/
│
├── 🟢 src/config.py             Settings from .env (DB URL, JWT secret, token lifetimes)
├── 🟢 src/main.py               FastAPI() app; mounts each domain router under /api/v1
│
├── src/db/
│   └── 🟢 main.py               async engine + session_factory + get_session() DI provider
│
├── src/books/                   ── DOMAIN MODULE (the reference CRUD example) ──
│   ├── 🟡 model.py              Book table (SQLModel, table=True)
│   ├── 🟠 schema.py             BookCreate / BookUpdate (validated input shapes)
│   ├── 🟣 service.py            BookService — get_all / get_by_id / create / update / delete
│   ├── 🔵 router.py             /books endpoints; whole router guarded by get_current_user
│   └── 🟢 book_data.py          seed/sample data
│
├── src/auth/                    ── DOMAIN MODULE (users + JWT auth) ──
│   ├── 🟡 model.py              User table + RefreshToken table
│   ├── 🟠 schema.py             UserCreate / UserRead / TokenPair / RefreshRequest
│   ├── 🔴 utils.py              hash/verify password (bcrypt) + encode/decode JWT
│   ├── 🟣 service.py            UserService (auth) + TokenService (issue/rotate/revoke)
│   ├── 🔴 dependencies.py       get_current_user guard + service providers
│   └── 🔵 router.py             /auth: register, login, refresh, logout, me, {id}
│
├── ⚫ alembic/                   Migration runtime (env.py) + versions/
│   └── versions/
│       ├── ⚫ bc6d3dfac8a9_create_user_table.py
│       └── ⚫ a1b2c3d4e5f6_add_refresh_token_table.py
├── ⚫ alembic.ini               Alembic CLI config
│
├── .env                         Secrets & DB URL (never committed)
├── pyproject.toml / uv.lock     Dependencies (managed with uv)
└── docs/                        This guide + the mastery roadmap
```

> **The golden rule of this layout:** the arrow of a request is always
> `🔵 router → 🟣 service → 🟡 model/DB`. A router never writes SQL; a service never
> raises `HTTPException`. That one discipline is what keeps every module testable and swappable.

### Per-file: purpose + key snippet

<details open>
<summary><b>🟢 src/config.py</b> — one typed place for all settings, loaded from <code>.env</code></summary>

Pydantic-settings reads env vars, casts them to the declared types, and fails loudly at startup if a required one (like `JWT_SECRET_KEY`) is missing.

```python
class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET_KEY: str                       # REQUIRED — no default, must be in .env
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    model_config = {"env_file": ".env"}

Config = Settings()                           # import this everywhere
```
</details>

<details>
<summary><b>🟢 src/main.py</b> — the app object; wires domain routers together</summary>

Each domain owns its own `APIRouter`; `main.py` just mounts them under a shared version prefix. No `init_db()` here — **Alembic owns the schema** (see §3.7).

```python
app = FastAPI(title="Book Store API")
app.include_router(books_router, prefix="/api/v1")
app.include_router(auth_router,  prefix="/api/v1")
```
</details>

<details>
<summary><b>🟢 src/db/main.py</b> — the engine, the session factory, and the session DI provider</summary>

One engine per process (it holds a connection pool). `get_session` is a `yield` dependency: code before `yield` runs per-request, cleanup after `yield` runs once the response is sent.

```python
async_engine = create_async_engine(url=Config.DATABASE_URL, echo=True)
session_factory = async_sessionmaker(bind=async_engine, class_=AsyncSession, expire_on_commit=False)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with session_factory() as session:
        yield session
```
</details>

<details>
<summary><b>🟡 model.py</b> (books / auth) — tables as Python classes</summary>

`table=True` registers the class on `SQLModel.metadata` (what Alembic diffs against). UUID PK, `default_factory=utcnow` timestamps, `unique=True, index=True` where the DB itself should enforce uniqueness and speed up lookups.

```python
class User(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    email: str = Field(..., max_length=255, unique=True, index=True)
    hashed_password: str                      # only the bcrypt hash is ever stored
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=utcnow)
```
</details>

<details>
<summary><b>🟠 schema.py</b> (books / auth) — the API contract, kept separate from the table</summary>

Input schemas validate what the client sends (`password`, not `hashed_password`). Output schemas control what leaks out — `UserRead` deliberately has **no** password field.

```python
class UserCreate(BaseModel):                  # what the client SENDS
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=72)   # 72 = bcrypt's hard limit

class UserRead(BaseModel):                    # what the API RETURNS — no hash, ever
    id: UUID
    email: str
    is_active: bool
    model_config = {"from_attributes": True}  # build directly from an ORM object
```
</details>

<details>
<summary><b>🟣 service.py</b> (books / auth) — all DB logic, HTTP-agnostic</summary>

A service takes a `session` and owns the queries/commits. It returns `None`/`bool` on "not found" or "conflict" instead of raising HTTP errors — the router decides the status code.

```python
class BookService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, payload: BookCreate) -> Book:
        book = Book(**payload.model_dump())
        self.session.add(book)                # stage
        await self.session.commit()           # write
        await self.session.refresh(book)      # re-read (populates created_at, etc.)
        return book
```
</details>

<details>
<summary><b>🔵 router.py</b> (books / auth) — HTTP surface, resolves services via <code>Depends</code></summary>

The router maps URLs to service calls and turns `None` into the right status code. Auth is attached at the **router** level so no future endpoint can forget it.

```python
router = APIRouter(prefix="/books", tags=["books"],
                   dependencies=[Depends(get_current_user)])   # every route needs a token

@router.get("/{book_id}", response_model=Book)
async def get_book(book_id: UUID, service: BookService = Depends(get_book_service)):
    book = await service.get_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail=f"Book {book_id} not found")
    return book
```
</details>

<details>
<summary><b>🔴 src/auth/utils.py</b> — password hashing + JWT encode/decode</summary>

Bcrypt with a per-call random salt (rainbow-table resistant). Every JWT carries a `type` (access/refresh) and a `jti` (unique id) so tokens can't be confused and refresh tokens can be tracked.

```python
def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()

def encode_token(*, subject: UUID, token_type: str, jti: UUID, expires_at: datetime) -> str:
    payload = {"sub": str(subject), "type": token_type, "jti": str(jti),
               "iat": datetime.now(timezone.utc), "exp": expires_at}
    return jwt.encode(payload, Config.JWT_SECRET_KEY, algorithm=Config.JWT_ALGORITHM)
```
</details>

<details>
<summary><b>🔴 src/auth/dependencies.py</b> — the <code>get_current_user</code> guard</summary>

The single choke point for "is this request authenticated?". Rejects (`401`) anything that isn't a valid, unexpired **access** token belonging to an existing, active user.

```python
async def get_current_user(token: str = Depends(oauth2_scheme),
                           service: UserService = Depends(get_user_service)) -> User:
    payload = decode_token(token)                       # raises on bad/expired token
    if payload.get("type") != ACCESS_TOKEN_TYPE:        # refuse refresh tokens here
        raise _credentials_error
    user = await service.get_by_id(UUID(payload["sub"]))
    if user is None or not user.is_active:
        raise _credentials_error
    return user
```
</details>

---

## 2. Topics Index

Everything this boilerplate teaches, and where to see it working. *Add a row here whenever you add a concept.*

| # | Topic | Deep-dive | Canonical snippet in code |
|---|-------|-----------|---------------------------|
| 1 | ORM basics (SQLModel = SQLAlchemy + Pydantic) | [§3.1](#31-database--orm-sqlmodel) | `src/books/model.py` |
| 2 | Async engine, connection pool, sessions | [§3.1](#31-database--orm-sqlmodel) | `src/db/main.py` |
| 3 | Defining a table (`table=True`, UUID PK, indexes) | [§3.1](#31-database--orm-sqlmodel) | `src/auth/model.py::User` |
| 4 | The layered pattern (router → service → db) | [§3.2](#32-the-layered-pattern--dependency-injection) | `books/{router,service}.py` |
| 5 | Dependency Injection (`Depends`, `yield` sessions) | [§3.2](#32-the-layered-pattern--dependency-injection) | `db/main.py::get_session` |
| 6 | Async & why it matters for DB I/O | [§3.2](#32-the-layered-pattern--dependency-injection) | every `async def` service method |
| 7 | CRUD operations (add/commit/refresh, `exclude_unset`) | [§3.3](#33-crud-operations) | `src/books/service.py` |
| 8 | Request vs response schemas (contract separation) | [§3.4](#34-schemas--validation) | `src/auth/schema.py` |
| 9 | Path & query parameters, `Query(...)` validation | [§3.5](#35-path--query-parameters--route-ordering) | `books/router.py` params |
| 10 | Route ordering (specific before parameterised) | [§3.5](#35-path--query-parameters--route-ordering) | — (rule of thumb) |
| 11 | User signup + bcrypt password hashing | [§3.6](#36-users--password-hashing) | `auth/utils.py`, `auth/service.py::create` |
| 12 | Alembic migrations (why, wiring, daily commands) | [§3.7](#37-alembic-migrations) | `alembic/env.py`, `alembic/versions/` |
| 13 | JWT auth: access + refresh tokens | [§3.8](#38-jwt-authentication-access--refresh) | `auth/utils.py`, `auth/service.py::TokenService` |
| 14 | Protecting endpoints (`get_current_user`) | [§3.8](#38-jwt-authentication-access--refresh) | `auth/dependencies.py` |
| 15 | Refresh rotation, reuse detection, logout | [§3.8](#38-jwt-authentication-access--refresh) | `auth/service.py::TokenService.rotate` |

---

## 3. Concept Deep-Dives

### 3.1 Database & ORM (SQLModel)

An **ORM** lets you work with tables as Python classes instead of raw SQL. SQLModel sits on **SQLAlchemy** (the ORM engine) and **Pydantic** (validation) — one class does both.

```python
# without ORM:  INSERT INTO book (title) VALUES ('Clean Code');
book = Book(title="Clean Code", author="Martin")   # with ORM
session.add(book); await session.commit()
```

**Engine** — the single connection point, created once at startup. It doesn't open a connection immediately; it builds a **connection pool** and hands out connections on demand. `echo=True` logs every SQL statement (great in dev).

**Session** — one *unit of work* (a shopping basket): collect `add`/`delete`/`setattr` operations, then `commit` them together. `expire_on_commit=False` keeps objects usable after commit.

**Defining a table** — any `SQLModel` subclass with `table=True` maps to a table (class name → table name, fields → columns). `SQLModel.metadata` tracks all such classes — this is what both `create_all` and Alembic autogenerate read.

> This repo uses **Postgres via the async `asyncpg` driver** (`postgresql+asyncpg://…`), so every DB call is awaited.

### 3.2 The Layered Pattern & Dependency Injection

```
router.py   →   service.py   →   database
(HTTP)          (business)       (SQLAlchemy)
```

- **Router** handles HTTP — paths, status codes, raising 404s.
- **Service** handles DB logic — queries, commits, business rules.
- Keeping them separate means the router never touches SQL and the service never knows about HTTP.

**Dependency Injection** — `Depends` runs a function and injects its return value. FastAPI resolves the whole chain automatically: you declare what you need, it figures out what to call first.

```python
# get_session (yield) → get_book_service (wraps session) → endpoint (gets ready service)
async def get_book_service(session: AsyncSession = Depends(get_session)) -> BookService:
    return BookService(session)
```

`get_session` uses `yield`, not `return`: it's a context-manager dependency — setup before `yield`, teardown after the response.

**Why async?** DB calls wait on network round-trips to Postgres. `async/await` lets the server serve other requests during that wait instead of blocking. Every method that touches the DB is `async def` and every DB call is `await`ed.

### 3.3 CRUD Operations

All five live in `src/books/service.py` — the reference implementation:

| Op | Core call | Note |
|----|-----------|------|
| Read all | `(await session.execute(select(Book))).scalars().all()` | `select(Book)` = `SELECT * FROM book` |
| Read one | `await session.get(Book, id)` | by primary key, no `WHERE` needed |
| Create | `session.add(obj)` → `commit()` → `refresh(obj)` | `refresh` repopulates server-set fields |
| Update | `setattr` from `model_dump(exclude_unset=True)` → `commit` | only fields the client actually sent |
| Delete | `await session.delete(obj)` → `commit()` | |

`exclude_unset=True` is the key to a correct `PATCH`/`PUT`: it skips fields the client omitted so you don't overwrite them with defaults.

### 3.4 Schemas & Validation

Table models and API schemas are **deliberately separate**:

- **Input schema** (`UserCreate`, `BookCreate`) — validates what comes in. Constraints live here: `Field(min_length=8, max_length=72)`, `EmailStr`, `ge=1000, le=2100`.
- **Output schema** (`UserRead`) — controls what goes out. It has no `hashed_password` field, so a hash can never leak in a response even by accident. Use `model_config = {"from_attributes": True}` to build it straight from an ORM object.

> `books` reuses its table model as the `response_model` — fine, because nothing on it is sensitive. `auth` splits them because a password hash must never be serialized.

### 3.5 Path & Query Parameters + Route Ordering

- **Path params** — declared as `{name}` in the URL; FastAPI type-casts them (`/books/abc` where an `int`/`UUID` is expected → automatic **422**). Mandatory.
- **Query params** — any function arg *not* in the path (`?author=Martin&limit=5`). Use `Query(...)` when you need validation or `/docs` descriptions:

```python
def list_books(author: str | None = Query(None, description="Filter by author"),
               limit: int = Query(10, ge=1, le=100)): ...
```

- **Route ordering** — FastAPI matches **top-to-bottom**. Put specific paths *before* parameterised ones, or `/books/popular` gets swallowed by `/books/{book_id}` and cast to the param's type → 422.

### 3.6 Users & Password Hashing

Signup follows the same layered pattern as `books`. Two `utils.py` helpers wrap bcrypt:

```python
hash_password("secret")          # -> "$2b$12$..."  (fresh random salt each call)
verify_password("secret", hash)  # -> True / False
```

`UserService.create()` checks `get_by_email()` first and returns `None` on conflict (the router turns that into `409`). The plaintext password is never persisted — only the bcrypt hash. Bcrypt's max input is **72 bytes**, which is why `UserCreate.password` caps at 72.

### 3.7 Alembic Migrations

A **migration** is a versioned, ordered script that changes the DB schema. Each knows its predecessor (`down_revision`), forming a chain you can `upgrade`/`downgrade`.

**Why not `create_all()`?** It only *adds tables that don't exist* — it can't alter an existing table (add/rename a column, add a constraint) and keeps no history. The moment a table already holds real data, you need migrations. Alembic also makes every environment reach the exact same schema by replaying the same scripts.

> That's why `main.py` no longer calls `init_db()`: with Alembic in charge, `create_all` and migrations would fight over who owns the schema. **Alembic is the single source of truth.**

**Two customizations in `alembic/env.py`:**
1. Pull the real DB URL from the app config: `config.set_main_option("sqlalchemy.url", Config.DATABASE_URL)`.
2. Import **every** model module so its table registers on `SQLModel.metadata` before autogenerate diffs it. *Any new module under `src/` must be imported here or Alembic won't see its table.* (`script.py.mako` also has `import sqlmodel` added, or autogenerated files `NameError` on `sqlmodel.sql.sqltypes.AutoString`.)

**Daily commands:**
```bash
uv run alembic revision --autogenerate -m "add is_active to user"   # generate (always read it!)
uv run alembic upgrade head        # apply
uv run alembic downgrade -1        # roll back one
uv run alembic current | history   # inspect
```

### 3.8 JWT Authentication (access + refresh)

Users authenticate **once** and get two JWTs signed with one secret:

- **Access token** — short-lived (**15 min**), sent on every request (`Authorization: Bearer <token>`). Pure stateless JWT: verify signature + expiry, no DB lookup. Fast, but **can't be revoked early** — which is fine because it dies fast.
- **Refresh token** — long-lived (**7 days**), used *only* at `POST /auth/refresh` to mint a new access token. Each one has a `refresh_token` **row** (keyed by its `jti`), which is what makes it **revocable** and **single-use**.

**Why two?** One unavoidable tension: a token used *constantly* wants to be short-lived (low leak blast-radius), but a token that keeps you logged in *for days* wants to be long-lived. Split the job: the access token is used constantly but expires fast; the refresh token is used rarely but lives long.

```
login (password, once)
        │
        ▼
   ┌──────────────┐   used on every request (15 min)   ┌───────────┐
   │ access token │ ─────────────────────────────────▶ │  your API │
   └──────────────┘                                     └───────────┘
        ▲
        │ when it expires → swap for a new one (no password)
   ┌──────────────┐
   │ refresh token│ ──────────▶  POST /auth/refresh  (7 days)
   └──────────────┘
```

**Endpoints** (all under `/api/v1`):

| Method & path | Auth | Body / form | Returns |
|---|---|---|---|
| `POST /auth/register` | no | JSON `UserCreate` | `201` user |
| `POST /auth/login` | no | **form** `username`(=email), `password` | `200` token pair |
| `POST /auth/refresh` | refresh token | JSON `{refresh_token}` | `200` new pair |
| `POST /auth/logout` | refresh token | JSON `{refresh_token}` | `204` |
| `GET /auth/me` | **access token** | — | `200` current user |
| `GET /auth/{id}` | **access token** | — | `200` user |
| `GET/POST/... /books` | **access token** | — | book data |

> `login` uses the OAuth2 **password form** (`username`+`password`, not JSON) on purpose — it's the FastAPI convention and it's what makes Swagger UI's **Authorize** button work. Put the email in `username`.

**Protecting your own endpoints:**
```python
# whole router:
router = APIRouter(prefix="/books", dependencies=[Depends(get_current_user)])
# single endpoint + get the user:
async def profile(current_user: User = Depends(get_current_user)):
    return {"email": current_user.email}
```

**Design decisions worth remembering:**
- **One secret, two types.** Every JWT has a `type` claim; `get_current_user` refuses refresh tokens, `/refresh` refuses access tokens.
- **Rotation (single-use).** Each `/refresh` revokes the presented token and issues a fresh pair — a refresh token works exactly once.
- **Reuse detection.** Presenting an already-rotated token = likely theft → revoke **all** of that user's refresh tokens (`revoke_all_for_user`), forcing a fresh login everywhere.
- **No user enumeration.** `login` returns the same `401` for unknown email vs wrong password, and `authenticate` runs a hash compare even when the user doesn't exist, so timing doesn't leak which emails are registered.
- **Logout is best-effort for access tokens.** A stateless access token stays valid until it expires; that's the trade-off for not hitting the DB per request. Keep `ACCESS_TOKEN_EXPIRE_MINUTES` small. Logout revokes the *refresh* token so no new access tokens can be minted.

**Config** (`.env`):
```dotenv
JWT_SECRET_KEY=<long random string>   # REQUIRED; different per environment, never commit prod
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
```
```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"   # generate a strong secret
uv run alembic upgrade head                                    # creates the refresh_token table
```

---

## Appendix — Quick Start

```bash
uv sync                                   # install deps
cp .env.example .env                      # set DATABASE_URL + JWT_SECRET_KEY
uv run alembic upgrade head               # build the schema
uv run uvicorn src.main:app --reload      # run → http://localhost:8000/docs
```

Then in Swagger (`/docs`): **register → Authorize** (email as username) → call protected `/books`.

---

*This is an evolving document. When you add a module, feature, or concept: update the [figure](#1-the-structure-figure), add a [topics-index](#2-topics-index) row, and (if it needs the "why") a deep-dive section.*
