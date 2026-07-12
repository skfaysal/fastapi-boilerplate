"""Kafka client — the event bus between the API and the Mongo activity log.

Producer side (this process): `ActivityService.record()` publishes an event here
instead of writing to Mongo directly. Consumer side (a *separate* process, see
`src/activity/consumer.py`) reads the topic and does the actual Mongo insert.

Why: decouples the request path from Mongo entirely (publishing to Kafka is
fire-and-forget from the API's point of view), makes events durable and
replayable instead of silently dropped on a Mongo outage, and lets more
consumers subscribe later without touching a single router.

Like the Mongo client (`src/db/mongo.py`), Kafka is treated as optional
infrastructure: if the broker isn't reachable at startup, the app still boots
and activity events are dropped (logged loudly), never blocking a request.
"""

import json
import logging

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from src.config import Config

logger = logging.getLogger("app")

ACTIVITY_TOPIC = "activity-events"

_producer: AIOKafkaProducer | None = None


async def start_producer() -> None:
    """Create and start the producer. Call once, from the app's lifespan startup."""
    global _producer
    producer = AIOKafkaProducer(
        bootstrap_servers=Config.KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        acks="all",                 # wait for full ISR ack — no silently lost events
        enable_idempotence=True,    # producer retries never create duplicate messages
    )
    await producer.start()
    _producer = producer


async def stop_producer() -> None:
    global _producer
    if _producer is not None:
        await _producer.stop()
        _producer = None


def get_producer() -> AIOKafkaProducer | None:
    """`None` means Kafka wasn't reachable at startup — callers must handle that."""
    return _producer


def make_consumer(group_id: str) -> AIOKafkaConsumer:
    """Build a consumer for the activity-events topic.

    `enable_auto_commit=False` — the consumer (src/activity/consumer.py) commits
    manually, only after the Mongo write succeeds, so a crash mid-processing
    re-delivers the event instead of silently losing it.
    """
    return AIOKafkaConsumer(
        ACTIVITY_TOPIC,
        bootstrap_servers=Config.KAFKA_BOOTSTRAP_SERVERS,
        group_id=group_id,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        auto_offset_reset="earliest",
        enable_auto_commit=False,
    )
