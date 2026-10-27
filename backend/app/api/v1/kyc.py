from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_roles
from app.core.database import get_db_session
from app.core.middleware import get_client_ip
from app.models.enums import ApplicationStatus, UserRole, VerificationStatus
from app.models.intern_profile import InternProfile
from app.models.user import User
from app.models.verification_log import VerificationLog
from app.schemas.verification import (
    KYCInitiateOTPRequest,
    KYCInitiateOTPResponse,
    KYCVerifyOTPRequest,
    KYCVerifyOTPResponse,
    VerificationLogResponse,
)
from app.services.audit_service import record_audit_log
from app.services.kyc_gateway import kyc_gateway_service

router = APIRouter(prefix="/kyc", tags=["Identity Verification (KYC)"])


@router.post("/initiate-otp", response_model=KYCInitiateOTPResponse)
async def initiate_kyc_otp(
    payload: KYCInitiateOTPRequest,
    request: Request,
    current_user: User = Depends(require_roles([UserRole.CANDIDATE])),
    db: AsyncSession = Depends(get_db_session),
) -> KYCInitiateOTPResponse:
    profile = (
        await db.execute(
            select(InternProfile).where(InternProfile.user_id == current_user.user_id)
        )
    ).scalar_one_or_none()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submit your intern profile before initiating identity verification.",
        )

    if profile.application_status != ApplicationStatus.SUBMITTED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Identity verification cannot be initiated from status '{profile.application_status}'.",
        )

    # Process raw ID in volatile memory and immediately clear from request object
    raw_id = payload.id_number
    payload.id_number = "[DISCARDED]"

    session = await kyc_gateway_service.initiate_otp(
        profile_id=profile.profile_id,
        id_type=payload.id_type,
        raw_id_number=raw_id,
    )
    del raw_id

    await record_audit_log(
        db,
        actor_id=current_user.user_id,
        action="KYC_OTP_INITIATED",
        target_entity=f"intern_profiles:{profile.profile_id}",
        ip_address=get_client_ip(request),
        details={
            "id_type": payload.id_type,
            "gateway_provider": session.gateway_provider,
            "transaction_reference": session.transaction_reference,
        },
    )
    await db.commit()

    masked_phone = (
        f"******{profile.phone_number[-4:]}"
        if len(profile.phone_number) >= 4
        else "******"
    )
    return KYCInitiateOTPResponse(
        session_token=session.session_token,
        gateway_provider=session.gateway_provider,
        masked_destination=masked_phone,
        expires_in_seconds=300,
        message="OTP dispatched to registered mobile number.",
    )


@router.post("/verify-otp", response_model=KYCVerifyOTPResponse)
async def verify_kyc_otp(
    payload: KYCVerifyOTPRequest,
    request: Request,
    current_user: User = Depends(require_roles([UserRole.CANDIDATE])),
    db: AsyncSession = Depends(get_db_session),
) -> KYCVerifyOTPResponse:
    profile = (
        await db.execute(
            select(InternProfile).where(InternProfile.user_id == current_user.user_id)
        )
    ).scalar_one_or_none()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Intern profile not found.",
        )

    is_verified, session = await kyc_gateway_service.verify_otp(
        profile_id=profile.profile_id,
        session_token=payload.session_token,
        otp=payload.otp,
    )

    verification_status = (
        VerificationStatus.SUCCESS.value if is_verified else VerificationStatus.FAILED.value
    )

    vlog = VerificationLog(
        profile_id=profile.profile_id,
        gateway_provider=session.gateway_provider,
        transaction_reference=session.transaction_reference,
        status=verification_status,
    )
    db.add(vlog)

    if is_verified:
        profile.application_status = ApplicationStatus.IDENTITY_VERIFIED.value

    await db.flush()

    await record_audit_log(
        db,
        actor_id=current_user.user_id,
        action="KYC_VERIFICATION_COMPLETED" if is_verified else "KYC_VERIFICATION_FAILED",
        target_entity=f"intern_profiles:{profile.profile_id}",
        ip_address=get_client_ip(request),
        details={
            "verification_id": str(vlog.verification_id),
            "gateway_provider": vlog.gateway_provider,
            "transaction_reference": vlog.transaction_reference,
            "status": vlog.status,
            "application_status": profile.application_status,
        },
    )
    await db.commit()
    await db.refresh(vlog)
    await db.refresh(profile)

    if not is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Identity verification failed: invalid OTP token.",
        )

    return KYCVerifyOTPResponse(
        message="Identity verified successfully.",
        application_status=ApplicationStatus(profile.application_status),
        verification=VerificationLogResponse.model_validate(vlog),
    )