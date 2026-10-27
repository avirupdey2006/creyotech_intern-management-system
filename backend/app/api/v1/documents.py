import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db_session
from app.core.encryption import crypto_engine
from app.core.middleware import get_client_ip
from app.models.document import Document
from app.models.enums import DocumentType, UserRole
from app.models.intern_profile import InternProfile
from app.models.user import User
from app.schemas.document import DocumentMetadataResponse, SignedUrlResponse
from app.services.audit_service import record_audit_log
from app.services.pdf_generator import pdf_generator_service

router = APIRouter(prefix="/documents", tags=["Documents & Signed URLs"])


async def _authorize_document_access(
    db: AsyncSession,
    document: Document,
    current_user: User,
) -> None:
    if current_user.role in (UserRole.ADMIN.value, UserRole.HR_REVIEWER.value):
        return
    profile = (
        await db.execute(
            select(InternProfile).where(InternProfile.profile_id == document.profile_id)
        )
    ).scalar_one_or_none()
    if not profile or profile.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to access this document.",
        )


@router.get("/my", response_model=List[DocumentMetadataResponse])
async def list_my_documents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> List[DocumentMetadataResponse]:
    profile = (
        await db.execute(
            select(InternProfile).where(InternProfile.user_id == current_user.user_id)
        )
    ).scalar_one_or_none()
    if not profile:
        return []

    stmt = (
        select(Document)
        .where(Document.profile_id == profile.profile_id)
        .order_by(Document.generated_at.desc())
    )
    docs = (await db.execute(stmt)).scalars().all()
    return [DocumentMetadataResponse.model_validate(d) for d in docs]


@router.get("/profile/{profile_id}", response_model=List[DocumentMetadataResponse])
async def list_profile_documents(
    profile_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> List[DocumentMetadataResponse]:
    if current_user.role not in (UserRole.ADMIN.value, UserRole.HR_REVIEWER.value):
        profile = (
            await db.execute(
                select(InternProfile).where(InternProfile.profile_id == profile_id)
            )
        ).scalar_one_or_none()
        if not profile or profile.user_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: cannot inspect another candidate's documents.",
            )

    stmt = (
        select(Document)
        .where(Document.profile_id == profile_id)
        .order_by(Document.generated_at.desc())
    )
    docs = (await db.execute(stmt)).scalars().all()
    return [DocumentMetadataResponse.model_validate(d) for d in docs]


@router.post("/{document_id}/signed-url", response_model=SignedUrlResponse)
async def create_document_signed_url(
    document_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> SignedUrlResponse:
    document = (
        await db.execute(select(Document).where(Document.document_id == document_id))
    ).scalar_one_or_none()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    await _authorize_document_access(db, document, current_user)

    signature, expires_at = crypto_engine.generate_signed_url_token(str(document.document_id))
    download_path = (
        f"/api/v1/documents/download/{document.document_id}"
        f"?expires={expires_at}&signature={signature}"
    )

    await record_audit_log(
        db,
        actor_id=current_user.user_id,
        action="DOCUMENT_SIGNED_URL_CREATED",
        target_entity=f"documents:{document.document_id}",
        ip_address=get_client_ip(request),
        details={
            "document_type": document.document_type,
            "expires_at": expires_at,
        },
    )
    await db.commit()

    return SignedUrlResponse(
        document_id=document.document_id,
        document_type=DocumentType(document.document_type),
        verification_code=document.verification_code,
        download_url=download_path,
        expires_at=expires_at,
        checksum_sha256=document.checksum_sha256,
    )


@router.get("/download/{document_id}")
async def download_document_via_signed_url(
    document_id: uuid.UUID,
    expires: int = Query(...),
    signature: str = Query(...),
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    is_valid = crypto_engine.verify_signed_url_token(
        str(document_id), expires_at=expires, signature=signature
    )
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Signed URL is invalid or has expired.",
        )

    document = (
        await db.execute(select(Document).where(Document.document_id == document_id))
    ).scalar_one_or_none()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document record not found.",
        )

    decrypted_pdf = await pdf_generator_service.read_decrypted_document(document)
    filename = f"{document.document_type.lower()}_{str(document.document_id)[:8]}.pdf"

    return Response(
        content=decrypted_pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Document-Checksum-SHA256": document.checksum_sha256,
        },
    )