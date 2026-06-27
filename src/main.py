from contextlib import asynccontextmanager
from fastapi import FastAPI

from src.books import model  # noqa: F401 — registers Book table with SQLModel metadata
from src.db.main import init_db
from src.books.router import router as books_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Book Store API", lifespan=lifespan)

app.include_router(books_router, prefix="/api/v1")
