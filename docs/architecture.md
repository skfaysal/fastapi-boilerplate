# Architecture & Feature Guide

How each production-grade feature is implemented in this boilerplate.

---

## 1. Layered Architecture — Router → Service → Repository

The codebase is split into three strict layers. Each layer has one job and does not cross into another layer's concern.

```
HTTP Request
    │
    ▼
┌─────────────────────────────────────────┐
│  Router  (TodoApp/routers/)             │
│  • Parse & validate HTTP input          │
│  • Delegate to service                  │
│  • Return HTTP response                 │
└──────────────────┬──────────────────────┘
                   │ speaks TodoRequest / UserData
                   ▼
┌─────────────────────────────────────────┐
│  Service  (TodoApp/services/)           │
│  • Business logic & rules               │
│  • Raises domain errors (AppError)      │
│  • No ORM, no HTTP — pure Python        │
└──────────────────┬──────────────────────┘
                   │ speaks AbstractTodoRepository
                   ▼
┌─────────────────────────────────────────┐
│  Repository interface  (interfaces.py)  │
│  • Defines the contract (ABC)           │
│  • Returns TodoData / UserData          │
│  • No SQL, no ORM details               │
└──────────────────┬──────────────────────┘
                   │ implemented by
                   ▼
┌─────────────────────────────────────────┐
│  Concrete repo  (todo_repository.py)    │
│  • The ONLY file that knows SQLAlchemy  │
│  • Maps ORM rows → TodoData dataclass   │
│  • Swap DB = swap this file only        │
└──────────────────┬──────────────────────┘
                   │
                   ▼
              Database (SQLite / PostgreSQL / anything)
```

### The shared language between layers — `domain.py`

All layers speak the same plain Python dataclasses. No ORM, no framework.

```python
# domain.py
@dataclass
class TodoData:
    id: int          # 0 means "not yet saved", repo sets the real id after create
    title: str
    description: str | None
    priority: int
    complete: bool
    owner_id: int
```

Routers return `TodoData` objects. Pydantic's `from_attributes=True` on `TodoResponse`
reads the dataclass attributes directly — no extra conversion step.

### Layer responsibilities

**Router** (`routers/`)
- Owns the HTTP boundary — methods, paths, status codes, request/response shapes.
- Reads input from the request (body, path params, headers) and hands it to the service.
- Must not contain business logic — only delegate and return.
- Example: receives a `TodoRequest` body, calls `service.create(data, user["id"])`, returns 201.

```python
@router.post("/todo", status_code=status.HTTP_201_CREATED)
async def create_todo(user: CurrentUserDep, service: TodoServiceDep, data: TodoRequest):
    service.create(data, user["id"])  # delegate — no logic here
```

**Service** (`services/`)
- Owns the business rules — what is allowed, in what order, under what conditions.
- The only layer that raises domain errors (`NotFoundError`, `ConflictError`, etc.).
- Has no knowledge of HTTP, SQL, or which database is being used.
- Receives and returns `TodoData` / `UserData` dataclasses — plain Python.
- Example: checks the todo belongs to the requesting user before deleting it.

```python
def delete(self, todo_id: int, owner_id: int) -> None:
    todo = self._repo.get_by_id_and_owner(todo_id, owner_id)  # returns TodoData
    if not todo:
        raise NotFoundError(f"Todo {todo_id} not found.")     # business rule
    self._repo.delete(todo)
```

**Repository interface** (`repositories/interfaces.py`)
- Defines the contract: what methods must exist and what types they accept/return.
- Services depend on this abstract class — never on the concrete implementation.
- This is the key to being ORM-agnostic: change the implementation, the contract stays.

```python
class AbstractTodoRepository(ABC):
    @abstractmethod
    def get_by_id_and_owner(self, todo_id: int, owner_id: int) -> TodoData | None: ...

    @abstractmethod
    def delete(self, data: TodoData) -> None: ...
```

**Concrete repository** (`repositories/todo_repository.py`)
- Implements the interface using SQLAlchemy (or any other tool).
- The only file that imports `Session`, `Todos`, or any ORM class.
- Contains a private `_to_data()` mapper that converts an ORM row to a `TodoData`.
- Swapping to MongoDB means writing a new class that satisfies the same interface.

```python
def _to_data(t: Todos) -> TodoData:          # ORM row → plain dataclass
    return TodoData(id=t.id, title=t.title, ...)

class TodoRepository(AbstractTodoRepository):
    def get_by_id_and_owner(self, todo_id: int, owner_id: int) -> TodoData | None:
        todo = self._db.query(Todos).filter(...).first()
        return _to_data(todo) if todo else None
```

---

### How dependency injection wires the layers

`TodoApp/dependencies.py` is the single place that assembles the chain using FastAPI's `Depends()`:

```python
# 1. Session is created per request (SQLAlchemy-specific, lives here only)
def get_db() -> Session: ...

# 2. Repository: concrete class returned, but typed as the abstract interface
def get_todo_repository(db: DbDep) -> AbstractTodoRepository:
    return TodoRepository(db)   # ← swap this line to change the database

# 3. Service receives the abstract interface — knows nothing about SQLAlchemy
def get_todo_service(repo: TodoRepoDep) -> TodoService:
    return TodoService(repo)

# 4. Router receives the service — all it needs to know
TodoServiceDep = Annotated[TodoService, Depends(get_todo_service)]
```

A router endpoint — no DB, no ORM, no SQL anywhere in sight:

```python
# routers/todos.py
@router.get("/", response_model=list[TodoResponse])
async def read_all(user: CurrentUserDep, service: TodoServiceDep):
    return service.get_all(user["id"])  # returns list[TodoData], serialised by Pydantic
```

### Swapping the database

To replace SQLAlchemy with any other database:

1. Write a new class that inherits `AbstractTodoRepository` and `AbstractUserRepository`.
2. In `dependencies.py`, change the return value of `get_todo_repository` and `get_user_repository` to return your new class.
3. Done — routers, services, schemas, auth, middleware: all untouched.

### Why this matters for a template

- Add new domain objects: add a dataclass to `domain.py` → add interface methods → implement → add service → add router.
- Unit-test services: pass a simple in-memory class that implements the interface. No HTTP server, no database needed.
- The SQLAlchemy coupling is contained to exactly two files: `repositories/user_repository.py` and `repositories/todo_repository.py`.

---

## 2. JWT Auth + OAuth2 Password Flow

Authentication follows the standard OAuth2 password flow that FastAPI and OpenAPI understand natively.

### Flow

```
Client                          API
  │                              │
  │── POST /auth/token ─────────>│
  │   (username + password form) │
  │                              │── verify password (bcrypt)
  │                              │── create JWT (HS256)
  │<── { access_token, type } ───│
  │                              │
  │── GET / (Authorization: Bearer <token>) ──>│
  │                              │── decode JWT
  │                              │── extract user payload
  │<── [ todos ] ────────────────│
```

### Where it lives

| File | Responsibility |
|---|---|
| `core/security.py` | `hash_password`, `verify_password`, `create_access_token`, `decode_access_token` |
| `services/auth_service.py` | `register()` and `login()` — business logic around users |
| `dependencies.py` | `get_current_user` — validates token on every protected request |
| `routers/auth.py` | `POST /auth/` (register) and `POST /auth/token` (login) |

### Token creation (`core/security.py`)

```python
def create_access_token(subject: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return jwt.encode({**subject, "exp": expire}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
```

The payload carries `sub` (username), `id`, and `role` — enough for every auth decision without a DB lookup per request.

### Token validation (`dependencies.py`)

```python
def get_current_user(token: Annotated[str, Depends(oauth2_bearer)]) -> dict:
    try:
        payload = decode_access_token(token)
    except JWTError:
        raise HTTPException(status_code=401, ...)
    if payload.get("sub") is None or payload.get("id") is None:
        raise HTTPException(status_code=401, ...)
    return {"username": payload["sub"], "id": payload["id"], "user_role": payload["role"]}
```

Every protected route simply declares `user: CurrentUserDep` and gets the decoded payload injected.

### Role-based access (admin)

Admin authorization is declared **once on the router** — not repeated per handler:

```python
# routers/admin.py
router = APIRouter(
    prefix="/admin",
    dependencies=[Depends(require_admin)],  # runs before every route in this file
)
```

`require_admin` in `dependencies.py` checks `user_role == "admin"` and raises `ForbiddenError` otherwise.

---

## 3. Rate Limiting — slowapi

Rate limiting is applied globally via [slowapi](https://github.com/laurents/slowapi), which wraps `limits` and integrates with FastAPI's middleware system.

### Setup (`main.py`)

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,          # rate limit per client IP
    default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"],
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

### Configuration

The limit is set in `.env` and read via `config.py`:

```env
RATE_LIMIT_PER_MINUTE=60
```

Change this value to adjust the global rate — no code change required.

### When the limit is exceeded

slowapi raises `RateLimitExceeded`, which is caught by `_rate_limit_exceeded_handler` and returns:

```http
HTTP/1.1 429 Too Many Requests
```

The RFC 7807 handler in `core/errors.py` ensures this also returns the standard problem-details JSON body.

---

## 4. Structured JSON Logging with Correlation IDs

Every log line is machine-readable JSON. Every line produced during a single HTTP request shares the same `correlation_id`, making it trivial to trace a request across all log output.

### Setup (`middleware/logging.py`)

```python
class _JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps({
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": correlation_id_var.get(""),  # ← from ContextVar
        })
```

`setup_logging()` is called once at startup (in the `lifespan` function in `main.py`) and replaces the root logger's handler with this formatter.

### Correlation ID middleware

```python
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")

async def correlation_id_middleware(request: Request, call_next: Callable) -> Response:
    cid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    token = correlation_id_var.set(cid)           # store for this request's context
    response = await call_next(request)
    correlation_id_var.reset(token)               # clean up after request
    response.headers["X-Request-ID"] = cid        # echo back to client
    return response
```

The middleware runs before every handler. Any `logging.getLogger(__name__).info(...)` call anywhere in the service or repository layer will automatically include the correct `correlation_id` for that request.

### Example log output

```json
{"timestamp": "2026-04-09 10:23:01", "level": "INFO", "logger": "access", "message": "GET / → 200 (12.4 ms)", "correlation_id": "a3f1c2d4-..."}
{"timestamp": "2026-04-09 10:23:01", "level": "WARNING", "logger": "TodoApp.core.errors", "message": "AppError [404]: Todo 99 not found.", "correlation_id": "a3f1c2d4-..."}
```

### Passing a correlation ID from a client

If the caller sends `X-Request-ID: my-trace-id`, the same value is used and echoed back. This lets upstream services (API gateways, frontend apps) propagate their own trace IDs.

---

## 5. OpenAPI Spec with Request/Response Examples

FastAPI generates the OpenAPI spec automatically. This boilerplate enriches it with:

- **Field-level examples** on every Pydantic schema
- **Route-level `summary`** on every endpoint
- **`responses` dict** documenting non-200 status codes per route

### Field examples (`schemas/`)

```python
class CreateUserRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, examples=["johndoe"])
    email: EmailStr = Field(..., examples=["john@example.com"])
    password: str = Field(..., min_length=8, examples=["securePass123"])
```

```python
class TodoRequest(BaseModel):
    title: str = Field(..., min_length=3, examples=["Buy groceries"])
    priority: int = Field(..., gt=0, lt=6, examples=[3])
```

These populate the "Try it out" form in `/docs` with realistic values.

### Route-level documentation (`routers/`)

```python
@router.post(
    "/",
    status_code=201,
    summary="Register a new user",
    responses={
        409: {"description": "Username or email already taken"},
        422: {"description": "Validation error"},
    },
)
```

### Docs visibility

In `main.py`, `/docs` and `/redoc` are hidden in production:

```python
app = FastAPI(
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
)
```

Set `ENVIRONMENT=production` in `.env` to disable them.

---

## 6. Global Error Handler — RFC 7807 Problem Details

All errors — validation failures, auth errors, not-found errors, unhandled exceptions — return the same JSON structure defined by [RFC 7807](https://datatracker.ietf.org/doc/html/rfc7807).

### Response format

```json
{
  "type": "about:blank",
  "title": "Not Found",
  "status": 404,
  "detail": "Todo 99 not found.",
  "instance": "/todo/99"
}
```

Content-Type is `application/problem+json`.

### Domain error hierarchy (`core/errors.py`)

```
AppError  (base)
├── NotFoundError       → 404
├── UnauthorizedError   → 401
├── ForbiddenError      → 403
└── ConflictError       → 409
```

Services raise domain errors. They contain no HTTP concepts:

```python
# services/todo_service.py
def get_one(self, todo_id: int, owner_id: int) -> Todos:
    todo = self._repo.get_by_id_and_owner(todo_id, owner_id)
    if not todo:
        raise NotFoundError(f"Todo {todo_id} not found.")
    return todo
```

### Handler registration (`core/errors.py`)

`register_error_handlers(app)` in `main.py` registers four handlers:

| Exception type | Converts to |
|---|---|
| `AppError` | Problem JSON using `exc.status_code`, `exc.title`, `exc.detail` |
| `StarletteHTTPException` | Problem JSON with title looked up from status code |
| `RequestValidationError` | 422 Problem JSON with field-level error list |
| `Exception` (catch-all) | 500 Problem JSON, full traceback logged |

```python
def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(request, exc):
        return _problem(request, exc.status_code, exc.title, exc.detail)

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request, exc):
        errors = [{"field": ..., "message": ...} for e in exc.errors()]
        return _problem(request, 422, "Validation Error", "...", {"errors": errors})

    @app.exception_handler(Exception)
    async def _unhandled(request, exc):
        logger.exception("Unhandled exception")
        return _problem(request, 500, "Internal Server Error", "An unexpected error occurred.")
```

### Validation error example

When a request body fails Pydantic validation, the response is:

```json
{
  "type": "about:blank",
  "title": "Validation Error",
  "status": 422,
  "detail": "One or more fields failed validation.",
  "instance": "/todo",
  "errors": [
    {"field": "body.priority", "message": "Input should be less than 6"},
    {"field": "body.title", "message": "String should have at least 3 characters"}
  ]
}
```
