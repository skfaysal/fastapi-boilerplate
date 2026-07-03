from fastapi import FastAPI

from src.books.router import router as books_router
from src.auth.router import router as auth_router

app = FastAPI(title="Book Store API")

app.include_router(books_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
