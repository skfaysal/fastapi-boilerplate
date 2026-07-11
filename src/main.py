import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import Config
from src.db.main import dispose_engine
from src.exceptions import register_exception_handlers
from src.middleware import RequestContextMiddleware
from src.books.router import router as books_router
from src.auth.router import router as auth_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown hook. Runs once, around the app's whole lifetime.

    The engine's connection pool is created lazily on first query, so there's
    nothing to warm up here — but on shutdown we dispose it cleanly instead of
    leaking connections. This is the modern replacement for ad-hoc setup/teardown.
    """
    logger.info("starting up")
    yield
    await dispose_engine()
    logger.info("shut down — engine disposed")


app = FastAPI(title="Book Store API", version="1.0.0", lifespan=lifespan)

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
