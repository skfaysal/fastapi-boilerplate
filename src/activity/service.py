import logging
from datetime import datetime, timezone

from fastapi import Depends

from src.db.mongo import get_activity_collection
from src.kafka import ACTIVITY_TOPIC, get_producer

logger = logging.getLogger("app")


class ActivityService:
    """Write side publishes to Kafka; read side reads the Mongo `activity` collection.

    The actual Mongo insert happens out-of-process, in the standalone consumer
    (src/activity/consumer.py) — this class never talks to Mongo for writes, only
    for `list_recent` (GET /activity reads whatever the consumer has persisted so far).
    """

    def __init__(self, collection):
        self.collection = collection

    async def record(self, event_type: str, user_id: str | None = None, detail: dict | None = None) -> None:
        """Publish an event to Kafka. Best-effort: never blocks or fails the request.

        Same contract as before the Kafka hop was added — callers don't need to change.
        """
        producer = get_producer()
        if producer is None:
            logger.warning("activity event dropped (kafka producer unavailable): %s", event_type)
            return
        payload = {
            "type": event_type,
            "user_id": user_id,
            "detail": detail or {},
            "ts": datetime.now(timezone.utc).isoformat(),
        }
        try:
            await producer.send_and_wait(
                ACTIVITY_TOPIC, value=payload, key=user_id.encode() if user_id else None
            )
        except Exception as exc:  # noqa: BLE001 — deliberately non-fatal
            logger.warning("activity event publish failed: %s", exc)

    async def list_recent(self, limit: int = 20, offset: int = 0) -> tuple[list[dict], int]:
        cursor = self.collection.find({}, {"_id": 0}).sort("ts", -1).skip(offset).limit(limit)
        items = await cursor.to_list(length=limit)
        total = await self.collection.count_documents({})
        return items, total


def get_activity_service(collection=Depends(get_activity_collection)) -> ActivityService:
    return ActivityService(collection)
