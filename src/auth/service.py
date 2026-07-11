from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, update

from src.config import Config
from src.auth.model import RefreshToken, User, utcnow
from src.auth.schema import UserCreate
from src.auth.utils import (
    ACCESS_TOKEN_TYPE,
    REFRESH_TOKEN_TYPE,
    encode_token,
    hash_password,
    verify_password,
)


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

    async def authenticate(self, email: str, password: str) -> User | None:
        """Return the user only if the email exists and the password matches.

        Note we still run `verify_password` even when no user is found — using a
        dummy hash — so the response time doesn't leak whether an email is
        registered (a timing side-channel).
        """
        user = await self.get_by_email(email.lower())
        if user is None:
            # Constant-ish work to avoid user-enumeration via timing.
            verify_password(password, hash_password("dummy-password-for-timing"))
            return None
        if not verify_password(password, user.hashed_password):
            return None
        if not user.is_active:
            return None
        return user


class TokenAlreadyUsedError(Exception):
    """A refresh token was replayed after it had already been rotated/revoked."""


class TokenService:
    """Issues, rotates, and revokes JWTs.

    Access tokens are pure stateless JWTs (never stored). Refresh tokens are also
    JWTs, but each one has a matching `refresh_token` row keyed by its `jti`, which
    is what makes them revocable and rotatable.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def issue_pair(self, user: User) -> tuple[str, str]:
        now = datetime.now(timezone.utc)

        access_token = encode_token(
            subject=user.id,
            token_type=ACCESS_TOKEN_TYPE,
            jti=uuid4(),
            expires_at=now + timedelta(minutes=Config.ACCESS_TOKEN_EXPIRE_MINUTES),
        )

        refresh_jti = uuid4()
        refresh_expires_at = now + timedelta(days=Config.REFRESH_TOKEN_EXPIRE_DAYS)
        self.session.add(
            RefreshToken(
                id=refresh_jti,
                user_id=user.id,
                # stored naive-UTC to match the User table's convention
                expires_at=refresh_expires_at.replace(tzinfo=None),
            )
        )
        await self.session.commit()

        refresh_token = encode_token(
            subject=user.id,
            token_type=REFRESH_TOKEN_TYPE,
            jti=refresh_jti,
            expires_at=refresh_expires_at,
        )
        return access_token, refresh_token

    async def rotate(self, refresh_jti: UUID, user: User) -> tuple[str, str]:
        """Revoke the presented refresh token and issue a brand-new pair.

        Rotation means a refresh token is single-use: every refresh invalidates the
        old token and hands back a new one. If a token that was already
        revoked/rotated is presented again, that's a replay (a sign it may have been
        stolen) — we revoke the user's entire token family and reject the request.
        """
        record = await self.session.get(RefreshToken, refresh_jti)

        if record is None or record.expires_at < utcnow():
            raise TokenAlreadyUsedError()

        if record.revoked:
            # Reuse of an already-rotated token → assume compromise, kill all sessions.
            await self.revoke_all_for_user(record.user_id)
            raise TokenAlreadyUsedError()

        record.revoked = True
        self.session.add(record)
        await self.session.commit()

        return await self.issue_pair(user)

    async def revoke(self, refresh_jti: UUID) -> None:
        """Revoke a single refresh token (logout of one session)."""
        record = await self.session.get(RefreshToken, refresh_jti)
        if record is not None and not record.revoked:
            record.revoked = True
            self.session.add(record)
            await self.session.commit()

    async def revoke_all_for_user(self, user_id: UUID) -> None:
        """Revoke every active refresh token for a user (logout everywhere)."""
        await self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked == False)  # noqa: E712
            .values(revoked=True)
        )
        await self.session.commit()
