from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.main import get_session
from src.auth.schema import UserCreate, UserRead
from src.auth.service import UserService

router = APIRouter(prefix="/auth", tags=["auth"])


async def get_user_service(session: AsyncSession = Depends(get_session)) -> UserService:
    return UserService(session)


@router.post("/register", response_model=UserRead, status_code=201)
async def register_user(payload: UserCreate, service: UserService = Depends(get_user_service)):
    user = await service.create(payload)
    if not user:
        raise HTTPException(status_code=409, detail=f"User with email {payload.email} already exists")
    return user


@router.get("/{user_id}", response_model=UserRead)
async def get_user(user_id: UUID, service: UserService = Depends(get_user_service)):
    user = await service.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    return user
