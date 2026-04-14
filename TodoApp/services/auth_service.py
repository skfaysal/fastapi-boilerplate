from ..core.errors import ConflictError, UnauthorizedError
from ..core.security import create_access_token, hash_password, verify_password
from ..domain import UserData
from ..repositories.interfaces import AbstractUserRepository
from ..schemas.auth import CreateUserRequest, Token


class AuthService:
    def __init__(self, repo: AbstractUserRepository) -> None:
        self._repo = repo

    def register(self, data: CreateUserRequest) -> None:
        if self._repo.get_by_username(data.username):
            raise ConflictError(f"Username '{data.username}' is already taken.")
        if self._repo.get_by_email(data.email):
            raise ConflictError(f"Email '{data.email}' is already registered.")

        self._repo.create(UserData(
            id=0,  # DB assigns the real id
            username=data.username,
            email=data.email,
            first_name=data.first_name,
            last_name=data.last_name,
            hashed_password=hash_password(data.password),
            is_active=True,
            role=data.role,
            phone_number=data.phone_number,
        ))

    def login(self, username: str, password: str) -> Token:
        user = self._repo.get_by_username(username)
        if not user or not verify_password(password, user.hashed_password):
            raise UnauthorizedError("Incorrect username or password.")
        token = create_access_token({"sub": user.username, "id": user.id, "role": user.role})
        return Token(access_token=token)
