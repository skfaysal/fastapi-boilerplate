"""Test fixtures.

Two things every test needs, both solved with `app.dependency_overrides`:
- a **real but throwaway DB** — an in-memory SQLite engine, so tests exercise real
  SQL through the services without touching Postgres;
- optional **auth bypass** — swap `get_current_user` for a fake user so protected
  routes are reachable without minting real JWTs.

The client drives the ASGI app in-process via `httpx.ASGITransport` (no running server).
"""

import os

# Config is validated at import time, so provide required env before importing the app.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")

from uuid import uuid4  # noqa: E402

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402
from sqlmodel import SQLModel  # noqa: E402

import src.books.model  # noqa: F401,E402  (register tables on SQLModel.metadata)
import src.auth.model  # noqa: F401,E402
from src.auth.dependencies import get_current_user  # noqa: E402
from src.auth.model import User  # noqa: E402
from src.db.main import get_session  # noqa: E402
from src.main import app  # noqa: E402


@pytest_asyncio.fixture
async def session() -> AsyncSession:
    # StaticPool keeps one shared connection so the in-memory schema persists across calls.
    engine = create_async_engine(
        "sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


@pytest_asyncio.fixture
async def client(session) -> AsyncClient:
    async def _override_get_session():
        yield session

    app.dependency_overrides[get_session] = _override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def auth_client(client) -> AsyncClient:
    """A client whose requests are pre-authenticated as a fake user."""
    fake_user = User(
        id=uuid4(), username="tester", email="tester@example.com",
        first_name="Test", last_name="User", hashed_password="x", is_active=True,
    )
    app.dependency_overrides[get_current_user] = lambda: fake_user
    return client
