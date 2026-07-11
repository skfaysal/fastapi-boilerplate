"""Promote (or demote) a user to admin by email.

Admins are never self-registered via the API (that would be an obvious privilege-
escalation hole). Instead, register the user normally, then promote them here.

Usage:
    uv run python scripts/make_admin.py alice@example.com          # grant admin
    uv run python scripts/make_admin.py alice@example.com --revoke # remove admin
"""

import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import select  # noqa: E402

from src.db.main import session_factory  # noqa: E402
from src.auth.model import User  # noqa: E402


async def set_admin(email: str, is_admin: bool) -> None:
    email = email.lower()  # emails are stored lowercased at registration
    async with session_factory() as session:
        user = (await session.execute(select(User).where(User.email == email))).scalars().first()
        if user is None:
            print(f"No user with email {email!r}. Register them first.")
            return
        user.is_admin = is_admin
        session.add(user)
        await session.commit()
    print(f"{'Granted' if is_admin else 'Revoked'} admin for {email}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("email")
    parser.add_argument("--revoke", action="store_true", help="remove admin instead of granting")
    args = parser.parse_args()
    asyncio.run(set_admin(args.email, is_admin=not args.revoke))
