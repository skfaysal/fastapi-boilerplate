from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.auth.model import User
from src.auth.schema import UserCreate
from src.auth.utils import hash_password


class UserService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalars().first()

    async def get_by_id(self, user_id: UUID) -> User | None:
        return await self.session.get(User, user_id)

    async def create(self, payload: UserCreate) -> User | None:
        existing_user = await self.get_by_email(payload.email)
        if existing_user:
            return None

        user = User(
            username=payload.username,
            email=payload.email,
            first_name=payload.first_name,
            last_name=payload.last_name,
            hashed_password=hash_password(payload.password),
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user
