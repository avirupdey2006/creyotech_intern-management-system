
import uuid

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_roles
from app.core.config import settings
from app.core.database import get_db_session
from app.core.middleware import get_client_ip
from app.models.audit_log import AuditLog
from app.models.document import Document
from app.models.enums import ApplicationStatus, DocumentType, UserRole
from app.models.intern_profile import InternProfile
from app.models.user import User
from app.schemas.audit import AuditLogResponse
from app.schemas.document import (
    DocumentMetadataResponse,
    StageDecisionRequest,
    StageDecisionResponse,
)
from app.schemas.intern import InternProfileResponse
from app.services.audit_service import record_audit_log
from app.services.kafka_producer import kafka_event_producer
from app.workers.kafka_consumer import process_document_and_email_event


router = APIRouter(prefix="/admin", tags=["HR Reviewer & Admin Operations"])


TRANSITION_RULES = {
    ApplicationStatus.PROVISIONAL_APPROVED.value: (
        ApplicationStatus.IDENTITY_VERIFIED.value,
        DocumentType.PROVISIONAL_OFFER.value,
        {UserRole.HR_REVIEWER.value, UserRole.ADMIN.value},
    ),
    ApplicationStatus.FINAL_APPROVED.value: (
        ApplicationStatus.PROVISIONAL_APPROVED.value,
        DocumentType.FINAL_OFFER.value,
        {UserRole.ADMIN.value},
    ),
    ApplicationStatus.COMPLETED.value: (
        ApplicationStatus.FINAL_APPROVED.value,
        DocumentType.COMPLETION_CERTIFICATE.value,
        {UserRole.ADMIN.value},
    ),
}


@router.get(
    "/applications",
    response_model=List[InternProfileResponse],
)
async def list_intern_applications(
    application_status: Optional[ApplicationStatus] = Query(default=None),
    current_user: User = Depends(
        require_roles([UserRole.HR_REVIEWER, UserRole.ADMIN])
    ),
    db: AsyncSession = Depends(get_db_session),
) -> List[InternProfileResponse]:
    stmt = select(InternProfile).order_by(
        InternProfile.created_at.desc()
    )

    if application_status is not None:
        stmt = stmt.where(
            InternProfile.application_status == application_status.value
        )

    profiles = (await db.execute(stmt)).scalars().all()

    return [
        InternProfileResponse.model_validate(profile)
        for profile in profiles
    ]


@router.post(
    "/applications/{profile_id}/decision",
    response_model=StageDecisionResponse,
)
async def decide_application_stage(
    profile_id: uuid.UUID,
    payload: StageDecisionRequest,
    request: Request,
    current_user: User = Depends(
        require_roles([UserRole.HR_REVIEWER, UserRole.ADMIN])
    ),
    db: AsyncSession = Depends(get_db_session),
) -> StageDecisionResponse:
    profile = (
        await db.execute(
            select(InternProfile).where(
                InternProfile.profile_id == profile_id
            )
        )
    ).scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Intern application profile not found.",
        )

    previous_status = profile.application_status
    target_status = payload.target_status
    client_ip = get_client_ip(request)
    idempotency_key = f"{profile.profile_id}:{target_status}"

    # Handle application rejection and revoke previously issued documents.
    if target_status == ApplicationStatus.REJECTED.value:
        if previous_status == ApplicationStatus.COMPLETED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot reject an already COMPLETED internship.",
            )

        profile.application_status = ApplicationStatus.REJECTED.value

        await db.execute(
            update(Document)
            .where(Document.profile_id == profile.profile_id)
            .values(is_valid=False)
        )

        await record_audit_log(
            db,
            actor_id=current_user.user_id,
            action="APPLICATION_REJECTED",
            target_entity=f"intern_profiles:{profile.profile_id}",
            ip_address=client_ip,
            details={
                "previous_status": previous_status,
                "new_status": target_status,
                "remarks": payload.remarks,
            },
        )

        await db.commit()

        return StageDecisionResponse(
            message=(
                "Application marked as REJECTED and any provisional "
                "documents revoked."
            ),
            profile_id=profile.profile_id,
            previous_status=ApplicationStatus(previous_status),
            new_status=ApplicationStatus.REJECTED,
            idempotency_key=idempotency_key,
            document=None,
        )

    # Validate stage transition rules and role permissions.
    if target_status not in TRANSITION_RULES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported target status: '{target_status}'.",
        )

    required_prev, doc_type, allowed_roles = TRANSITION_RULES[target_status]

    if current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Role '{current_user.role}' is not authorized to approve "
                f"'{target_status}'. Required: {sorted(allowed_roles)}"
            ),
        )

    if previous_status not in (required_prev, target_status):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Invalid stage transition from '{previous_status}' to "
                f"'{target_status}'. Expected current status: "
                f"'{required_prev}'."
            ),
        )

    # Apply any HR/Admin updates to appointment details before generating PDF.
    if payload.internship_role:
        profile.internship_role = payload.internship_role.strip()

    if payload.start_date:
        profile.start_date = payload.start_date

    if payload.end_date:
        profile.end_date = payload.end_date

    if payload.work_mode:
        profile.work_mode = payload.work_mode.strip()

    if payload.work_schedule:
        profile.work_schedule = payload.work_schedule.strip()

    if payload.reporting_manager:
        profile.reporting_manager = payload.reporting_manager.strip()

    if payload.address:
        profile.address = payload.address.strip()

    if payload.city:
        profile.city = payload.city.strip()

    if payload.state:
        profile.state = payload.state.strip()

    if payload.pin_code:
        profile.pin_code = payload.pin_code.strip()

    profile.application_status = target_status
    await db.flush()

    await record_audit_log(
        db,
        actor_id=current_user.user_id,
        action=f"STAGE_{target_status}",
        target_entity=f"intern_profiles:{profile.profile_id}",
        ip_address=client_ip,
        details={
            "previous_status": previous_status,
            "new_status": target_status,
            "remarks": payload.remarks,
            "idempotency_key": idempotency_key,
        },
    )

    event_payload = {
        "profile_id": str(profile.profile_id),
        "document_type": doc_type,
        "admin_approved_by": str(current_user.user_id),
        "idempotency_key": idempotency_key,
        "issuer_remarks": payload.remarks,
        "actor_ip": client_ip,
    }

    await kafka_event_producer.publish_event(
        settings.KAFKA_TOPIC_DOCUMENT_GENERATION,
        idempotency_key=idempotency_key,
        payload=event_payload,
    )

    doc_record, _ = await process_document_and_email_event(
        db,
        profile_id=profile.profile_id,
        document_type=doc_type,
        admin_approved_by=current_user.user_id,
        idempotency_key=idempotency_key,
        issuer_remarks=payload.remarks,
        actor_ip=client_ip,
    )

    await db.commit()
    await db.refresh(doc_record)

    return StageDecisionResponse(
        message=(
            f"Application transitioned to {target_status} and "
            f"{doc_type} (Code: {doc_record.verification_code}) dispatched."
        ),
        profile_id=profile.profile_id,
        previous_status=ApplicationStatus(previous_status),
        new_status=ApplicationStatus(target_status),
        idempotency_key=idempotency_key,
        document=DocumentMetadataResponse.model_validate(doc_record),
    )


@router.get(
    "/audit-logs",
    response_model=List[AuditLogResponse],
)
async def list_audit_logs(
    limit: int = Query(default=100, ge=1, le=500),
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db_session),
) -> List[AuditLogResponse]:
    stmt = (
        select(AuditLog)
        .order_by(AuditLog.timestamp.desc())
        .limit(limit)
    )

    logs = (await db.execute(stmt)).scalars().all()

    return [
        AuditLogResponse.model_validate(log)
        for log in logs
    ]
