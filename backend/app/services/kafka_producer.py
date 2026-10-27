import json
from typing import Any, Dict, Optional
from aiokafka import AIOKafkaProducer

from app.core.config import settings
from app.core.logging import pino_logger


class KafkaEventProducer:
    """
    Asynchronous Kafka Producer for IMS event streaming (Section 2 & 3.6).
    Replaces Redis/BullMQ as mandated by HR specification.
    """

    def __init__(self) -> None:
        self._producer: Optional[AIOKafkaProducer] = None
        self._broker_available: bool = False

    async def start(self) -> None:
        try:
            producer = AIOKafkaProducer(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                request_timeout_ms=3000,
                connections_max_idle_ms=10000,
            )
            await producer.start()
            self._producer = producer
            self._broker_available = True
            pino_logger.info(
                "Connected to Apache Kafka broker",
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            )
        except Exception as exc:
            self._producer = None
            self._broker_available = False
            pino_logger.warning(
                "Kafka broker not reachable at startup; using resilient in-process event fallback",
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                reason=str(exc),
            )

    async def stop(self) -> None:
        if self._producer is not None:
            try:
                await self._producer.stop()
            except Exception:
                pass
            finally:
                self._producer = None
                self._broker_available = False

    async def publish_event(
        self,
        topic: str,
        *,
        idempotency_key: str,
        payload: Dict[str, Any],
    ) -> bool:
        """
        Publishes an event to the specified Kafka topic keyed by idempotency_key.
        Returns True if sent to external Kafka broker, False if fallback mode is active.
        """
        envelope = {
            "idempotency_key": idempotency_key,
            "topic": topic,
            "payload": payload,
        }
        if self._producer and self._broker_available:
            try:
                await self._producer.send_and_wait(
                    topic,
                    key=idempotency_key,
                    value=envelope,
                )
                pino_logger.info(
                    "Published event to Kafka topic",
                    topic=topic,
                    idempotency_key=idempotency_key,
                )
                return True
            except Exception as exc:
                pino_logger.warning(
                    "Kafka publish failed; falling back to direct processor",
                    topic=topic,
                    idempotency_key=idempotency_key,
                    error=str(exc),
                )
        return False


kafka_event_producer = KafkaEventProducer()