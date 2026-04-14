from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .config import get_settings
from .core.errors import register_error_handlers
from .database import engine
from .middleware.logging import correlation_id_middleware, setup_logging
from .models import Base
from .routers import admin, auth, todos, users

settings = get_settings()

# Rate limiter — keyed by client IP, default applied globally
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"],
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging("DEBUG" if settings.DEBUG else "INFO")
    Base.metadata.create_all(bind=engine)  # dev convenience; use Alembic in prod
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Production-grade FastAPI boilerplate — layered architecture, "
        "JWT auth, rate limiting, structured logging, RFC 7807 errors."
    ),
    lifespan=lifespan,
    # Hide docs in production
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
)

# ── State ─────────────────────────────────────────────────────────────────────
app.state.limiter = limiter

# ── Middleware (outermost first) ──────────────────────────────────────────────
app.middleware("http")(correlation_id_middleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # tighten via settings in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Exception handlers ────────────────────────────────────────────────────────
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
register_error_handlers(app)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(todos.router)
app.include_router(admin.router)
app.include_router(users.router)


@app.get("/health", tags=["health"], summary="Health check")
async def health_check() -> dict:
    return {"status": "healthy", "version": settings.APP_VERSION}
