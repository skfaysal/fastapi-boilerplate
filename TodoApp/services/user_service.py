from ..core.errors import UnauthorizedError
from ..core.security import hash_password, verify_password
from ..domain import UserData
from ..repositories.interfaces import AbstractUserRepository
from ..schemas.user import UserVerification


class UserService:
    def __init__(self, repo: AbstractUserRepository) -> None:
        self._repo = repo

    def get_profile(self, user_id: int) -> UserData | None:
        return self._repo.get_by_id(user_id)

    def change_password(self, user_id: int, data: UserVerification) -> None:
        user = self._repo.get_by_id(user_id)  # UserData
        if not verify_password(data.password, user.hashed_password):
            raise UnauthorizedError("Current password is incorrect.")
        # Mutate the dataclass, then hand it back to the repo to persist.
        user.hashed_password = hash_password(data.new_password)
        self._repo.save(user)

    def change_phone_number(self, user_id: int, phone_number: str) -> None:
        user = self._repo.get_by_id(user_id)  # UserData
        user.phone_number = phone_number
        self._repo.save(user)
