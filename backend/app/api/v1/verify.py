from fastapi import APIRouter, Depends, HTTPException, Path, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.middleware import get_client_ip
from app.models.document import Document
from app.models.enums import ApplicationStatus, DocumentType
from app.models.intern_profile import InternProfile
from app.schemas.document import CertificateVerificationResponse
from app.services.audit_service import record_audit_log

router = APIRouter(prefix="/verify", tags=["Public Certificate Verification"])


def _format_duration(start_date, end_date) -> str:
    days = (end_date - start_date).days
    months = max(1, round(days / 30))
    start_str = start_date.strftime("%d %b %Y")
    end_str = end_date.strftime("%d %b %Y")
    return f"{start_str} to {end_str} ({months} {'Month' if months == 1 else 'Months'})"


@router.get(
    "/{verification_code}",
    response_model=CertificateVerificationResponse,
)
async def verify_certificate_by_code(
    request: Request,
    verification_code: str = Path(..., min_length=6, max_length=20),
    db: AsyncSession = Depends(get_db_session),
) -> CertificateVerificationResponse:
    normalized_code = (
        verification_code.strip().upper().replace("-", "").replace(" ", "")
    )
    if len(normalized_code) != 12 or not normalized_code.isalnum():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid verification code format. Expected a 12-character alphanumeric code.",
        )

    stmt = (
        select(Document, InternProfile)
        .join(InternProfile, Document.profile_id == InternProfile.profile_id)
        .where(Document.verification_code == normalized_code)
    )
    row = (await db.execute(stmt)).first()

    if not row:
        await record_audit_log(
            db,
            actor_id=None,
            action="PUBLIC_CERTIFICATE_VERIFY_FAILED",
            target_entity=f"verification_code:{normalized_code}",
            ip_address=get_client_ip(request),
            details={"reason": "CODE_NOT_FOUND"},
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No certificate or offer letter found matching this 12-character verification code.",
        )

    doc, profile = row
    is_currently_valid = bool(
        doc.is_valid and profile.application_status != ApplicationStatus.REJECTED.value
    )
    validity_status = "VALID" if is_currently_valid else "REVOKED"

    await record_audit_log(
        db,
        actor_id=None,
        action="PUBLIC_CERTIFICATE_VERIFIED",
        target_entity=f"documents:{doc.document_id}",
        ip_address=get_client_ip(request),
        details={
            "verification_code": normalized_code,
            "document_type": doc.document_type,
            "validity_status": validity_status,
        },
    )
    await db.commit()

    return CertificateVerificationResponse(
        verified=is_currently_valid,
        validity_status=validity_status,
        verification_code=doc.verification_code,
        document_type=DocumentType(doc.document_type),
        intern_name=profile.full_name,
        internship_designation=profile.internship_role,
        college_name=profile.college_name,
        start_date=profile.start_date,
        end_date=profile.end_date,
        duration_display=_format_duration(profile.start_date, profile.end_date),
        work_mode=profile.work_mode,
        reporting_manager=profile.reporting_manager,
        issued_at=doc.generated_at,
        issuer_remarks=doc.issuer_remarks,
        checksum_sha256=doc.checksum_sha256,
    )