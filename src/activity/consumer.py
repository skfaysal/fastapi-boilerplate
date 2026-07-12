"""Standalone consumer: activity-events (Kafka) -> activity collection (MongoDB).

Runs as its own process, independent of the API:

    uv run python -m src.activity.consumer

Why a separate process rather than a background task inside the API: it decouples
the Mongo writer's lifecycle from the API's — either can restart, crash, or scale
without affecting the other, and it's the same shape a real deployment would use
(a dedicated consumer worker). See docs/user_guide.md for the full walkthrough.

Delivery semantics: at-least-once. The Mongo write is retried a few times on
failure; if it still fails, the event is logged loudly and dropped rather than
wedging the consumer forever on one poison message. The offset is committed only
after that decision is made, so a crash *before* this point re-delivers the event
on restart (possible duplicate — acceptable for an audit log, never a silent loss).
"""

import asyncio
import logging
from datetime import datetime

from src.db.mongo import close_mongo, mongo_db
from src.kafka import ACTIVITY_TOPIC, make_consumer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("activity-consumer")

GROUP_ID = "activity-mongo-writer"


async def _persist_with_retry(collection, event: dict, attempts: int = 3) -> bool:
    # Kafka carries `ts` as an ISO string (JSON has no datetime type); restore a
    # real datetime before inserting so it stays a BSON date, consistent with
    # every other document already in the collection (mixed types break `sort`).
    event["ts"] = datetime.fromisoformat(event["ts"])
    for attempt in range(1, attempts + 1):
        try:
            await collection.insert_one(event)
            return True
        except Exception as exc:  # noqa: BLE001 — retried below, logged either way
            logger.warning("mongo write failed (attempt %d/%d): %s", attempt, attempts, exc)
            await asyncio.sleep(0.5 * attempt)
    return False


async def main() -> None:
    consumer = make_consumer(group_id=GROUP_ID)
    await consumer.start()
    collection = mongo_db["activity"]
    logger.info("started — topic=%s group=%s", ACTIVITY_TOPIC, GROUP_ID)
    try:
        async for msg in consumer:
            ok = await _persist_with_retry(collection, msg.value)
            if not ok:
                logger.error("dropping event after retries exhausted: %s", msg.value)
            # Always advance — a permanently-failing message must never wedge the consumer.
            await consumer.commit()
    finally:
        await consumer.stop()
        close_mongo()
        logger.info("stopped")


if __name__ == "__main__":
    asyncio.run(main())
