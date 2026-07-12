"""MongoDB connection — the NoSQL side of the app (polyglot persistence).

Postgres (SQLModel) stays the source of truth for entities (users, books); Mongo
holds the append-only *activity log*, where each event has a different shape and a
rigid SQL table would be the wrong tool.

The client is created at import but connects lazily, so the app still boots if Mongo
is down — activity writes are best-effort (see ActivityService.record).
"""

from motor.motor_asyncio import AsyncIOMotorClient

from src.config import Config

# serverSelectionTimeoutMS keeps failures fast when Mongo is unreachable (default is 30s).
mongo_client: AsyncIOMotorClient = AsyncIOMotorClient(
    Config.MONGO_URL, serverSelectionTimeoutMS=3000, uuidRepresentation="standard"
)
mongo_db = mongo_client[Config.MONGO_DB]


def get_activity_collection():
    """DI provider: the `activity` collection handle (no connection happens here)."""
    return mongo_db["activity"]


async def ping_mongo() -> None:
    await mongo_client.admin.command("ping")


def close_mongo() -> None:
    mongo_client.close()
