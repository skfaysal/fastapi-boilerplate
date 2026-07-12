import logging
from datetime import datetime, timezone

from fastapi import Depends

from src.db.mongo import get_activity_collection

logger = logging.getLogger("app")


class ActivityService:
    """Reads/writes the Mongo `activity` collection.

    Same layered idea as the SQL services (§05), but over a document store: no
    schema, no migrations — you just insert a dict.
    """

    def __init__(self, collection):
        self.collection = collection

    async def record(self, event_type: str, user_id: str | None = None, detail: dict | None = None) -> None:
        """Best-effort write. An audit log must never break the user's request, so a
        Mongo hiccup is logged and swallowed rather than raised."""
        try:
            await self.collection.insert_one(
                {
                    "type": event_type,
                    "user_id": user_id,
                    "detail": detail or {},
                    "ts": datetime.now(timezone.utc),
                }
            )
        except Exception as exc:  # noqa: BLE001 — deliberately non-fatal
            logger.warning("activity log write failed: %s", exc)

    async def list_recent(self, limit: int = 20, offset: int = 0) -> tuple[list[dict], int]:
        cursor = self.collection.find({}, {"_id": 0}).sort("ts", -1).skip(offset).limit(limit)
        items = await cursor.to_list(length=limit)
        total = await self.collection.count_documents({})
        return items, total


def get_activity_service(collection=Depends(get_activity_collection)) -> ActivityService:
    return ActivityService(collection)
