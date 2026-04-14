"""
SQLAlchemy implementation of AbstractUserRepository.

This is the ONLY file in the project that knows about the Users ORM model.
Everything above this layer (services, routers) works with UserData dataclasses.

_to_data() is a private mapper that converts an ORM row → plain UserData.
"""
from sqlalchemy.orm import Session

from ..domain import UserData
from ..models import Users
from .interfaces import AbstractUserRepository


def _to_data(u: Users) -> UserData:
    return UserData(
        id=u.id,
        username=u.username,
        email=u.email,
        first_name=u.first_name,
        last_name=u.last_name,
        hashed_password=u.hashed_password,
        is_active=u.is_active,
        role=u.role,
        phone_number=u.phone_number,
    )


class UserRepository(AbstractUserRepository):

    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_id(self, user_id: int) -> UserData | None:
        user = self._db.get(Users, user_id)
        return _to_data(user) if user else None

    def get_by_username(self, username: str) -> UserData | None:
        user = self._db.query(Users).filter(Users.username == username).first()
        return _to_data(user) if user else None

    def get_by_email(self, email: str) -> UserData | None:
        user = self._db.query(Users).filter(Users.email == email).first()
        return _to_data(user) if user else None

    def create(self, data: UserData) -> UserData:
        user = Users(
            username=data.username,
            email=data.email,
            first_name=data.first_name,
            last_name=data.last_name,
            hashed_password=data.hashed_password,
            is_active=data.is_active,
            role=data.role,
            phone_number=data.phone_number,
        )
        self._db.add(user)
        self._db.commit()
        self._db.refresh(user)
        return _to_data(user)  # returns with the real DB-assigned id

    def save(self, data: UserData) -> UserData:
        # Fetch the live ORM object, apply changes, persist.
        user = self._db.get(Users, data.id)
        user.hashed_password = data.hashed_password
        user.phone_number = data.phone_number
        user.is_active = data.is_active
        user.role = data.role
        self._db.commit()
        self._db.refresh(user)
        return _to_data(user)
