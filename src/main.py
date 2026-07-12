import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import Config
from src.db.main import dispose_engine
from src.db.mongo import close_mongo, ping_mongo
from src.exceptions import register_exception_handlers
from src.logging_config import configure_logging
from src.middleware import RequestContextMiddleware
from src.ratelimit import limiter
from src.books.router import router as books_router
from src.auth.router import router as auth_router
from src.activity.router import router as activity_router

configure_logging()
logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown hook. Runs once, around the app's whole lifetime.

    The engine's connection pool is created lazily on first use, so there's
    nothing to warm up here — but on shutdown we dispose it cleanly instead of
    leaking connections. This is the modern replacement for ad-hoc setup/teardown.
    """
    logger.info("starting up")
    try:
        await ping_mongo()
        logger.info("mongo connected")
    except Exception as exc:  # noqa: BLE001 — Mongo is optional; activity writes are best-effort
        logger.warning("mongo not reachable at startup: %s", exc)
    yield
    await dispose_engine()
    close_mongo()
    logger.info("shut down — engine disposed")


# Hide interactive docs outside dev — they leak your whole API surface.
_docs = {} if Config.ENVIRONMENT == "dev" else {"docs_url": None, "redoc_url": None, "openapi_url": None}

app = FastAPI(title="Book Store API", version="1.0.0", lifespan=lifespan, **_docs)

# Rate limiting (slowapi) needs the limiter on app.state; the 429 handler is
# registered alongside the other error handlers below.
app.state.limiter = limiter

# Middleware — outermost first. Request context (id + timing) wraps every request.
app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=Config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# One consistent {"error": {...}} shape for every failure.
register_exception_handlers(app)

app.include_router(books_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(activity_router, prefix="/api/v1")
