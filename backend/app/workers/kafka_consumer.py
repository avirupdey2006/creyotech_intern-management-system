import asyncio
import json
import uuid
from typing import Any, Dict, Optional
from aiokafka import AIOKafkaConsumer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.logging import pino_logger, setup_logging_and_sentry, trigger_sentry_alert
from app.models.document import Document
from app.models.intern_profile import InternProfile
from app.models.user import User
from app.services.audit_service import record_audit_log
from app.services.email_dispatcher import email_dispatcher_service
from app.services.pdf_generator import pdf_generator_service


async def process_document_and_email_event(
    db: AsyncSession,
    *,
    profile_id: uuid.UUID,
    document_type: str,
    admin_approved_by: uuid.UUID,
    idempotency_key: str,
    issuer_remarks: Optional[str] = None,
    actor_ip: str = "127.0.0.1",
) -> tuple[Document, dict]:
    """
    Idempotent workflow processor executed by the Kafka consumer worker (or in-process fallback):
    1. Generates & encrypts HR-formatted PDF document with 12-char verification code.
    2. Dispatches email notification with decrypted PDF attachment (once per idempotency_key).
    3. Records immutable audit trail entries.
    """
    profile = (
        await db.execute(
            select(InternProfile).where(InternProfile.profile_id == profile_id)
        )
    ).scalar_one_or_none()
    if not profile:
        raise ValueError(f"InternProfile {profile_id} not found for document generation.")

    candidate_user = (
        await db.execute(select(User).where(User.user_id == profile.user_id))
    ).scalar_one()

    doc_record, pdf_bytes, was_created = await pdf_generator_service.generate_and_store_document(
        db,
        profile=profile,
        document_type=document_type,
        admin_approved_by=admin_approved_by,
        idempotency_key=f"doc:{idempotency_key}",
        issuer_remarks=issuer_remarks,
    )

    if was_created:
        await record_audit_log(
            db,
            actor_id=admin_approved_by,
            action="DOCUMENT_GENERATED",
            target_entity=f"documents:{doc_record.document_id}",
            ip_address=actor_ip,
            details={
                "profile_id": str(profile.profile_id),
                "document_type": document_type,
                "verification_code": doc_record.verification_code,
                "checksum_sha256": doc_record.checksum_sha256,
                "idempotency_key": f"doc:{idempotency_key}",
            },
        )

    email_result = await email_dispatcher_service.dispatch_document_email(
        recipient_email=candidate_user.email,
        candidate_name=profile.full_name,
        document_type=document_type,
        pdf_bytes=pdf_bytes,
        idempotency_key=f"email:{idempotency_key}",
    )

    if email_result["status"] == "SENT":
        await record_audit_log(
            db,
            actor_id=admin_approved_by,
            action="NOTIFICATION_EMAIL_DISPATCHED",
            target_entity=f"intern_profiles:{profile.profile_id}",
            ip_address=actor_ip,
            details={
                "document_id": str(doc_record.document_id),
                "verification_code": doc_record.verification_code,
                "document_type": document_type,
                "recipient_email": candidate_user.email,
                "delivery_mode": email_result["delivery_mode"],
                "idempotency_key": f"email:{idempotency_key}",
            },
        )

    return doc_record, email_result


async def handle_kafka_message(envelope: Dict[str, Any]) -> None:
    """Processes a raw Kafka event envelope inside a managed database transaction."""
    payload = envelope.get("payload", {})
    idempotency_key = envelope.get("idempotency_key") or payload.get("idempotency_key")
    profile_id = uuid.UUID(payload["profile_id"])
    document_type = payload["document_type"]
    admin_approved_by = uuid.UUID(payload["admin_approved_by"])
    issuer_remarks = payload.get("issuer_remarks")
    actor_ip = payload.get("actor_ip", "kafka-worker")

    async with AsyncSessionLocal() as db:
        await process_document_and_email_event(
            db,
            profile_id=profile_id,
            document_type=document_type,
            admin_approved_by=admin_approved_by,
            idempotency_key=idempotency_key,
            issuer_remarks=issuer_remarks,
            actor_ip=actor_ip,
        )
        await db.commit()


async def run_kafka_consumer_worker() -> None:
    """Standalone long-running Kafka Consumer loop for Docker/Kubernetes/Render worker deployment."""
    setup_logging_and_sentry()
    topics = [
        settings.KAFKA_TOPIC_DOCUMENT_GENERATION,
        settings.KAFKA_TOPIC_EMAIL_NOTIFICATION,
    ]
    pino_logger.info(
        "Starting IMS Kafka Consumer Worker",
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        topics=topics,
        group_id=settings.KAFKA_CONSUMER_GROUP,
    )

    consumer = AIOKafkaConsumer(
        *topics,
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id=settings.KAFKA_CONSUMER_GROUP,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        enable_auto_commit=True,
        auto_offset_reset="earliest",
    )

    await consumer.start()
    try:
        async for msg in consumer:
            try:
                pino_logger.info(
                    "Kafka consumer received event",
                    topic=msg.topic,
                    partition=msg.partition,
                    offset=msg.offset,
                )
                await handle_kafka_message(msg.value)
            except Exception as exc:
                trigger_sentry_alert(
                    "Kafka worker failed processing message",
                    level="error",
                    context={"topic": msg.topic, "offset": msg.offset, "error": str(exc)},
                )
    finally:
        await consumer.stop()


if __name__ == "__main__":
    asyncio.run(run_kafka_consumer_worker())