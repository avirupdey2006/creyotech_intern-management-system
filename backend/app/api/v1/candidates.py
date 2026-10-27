from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_roles
from app.core.database import get_db_session
from app.core.middleware import get_client_ip
from app.models.enums import ApplicationStatus, UserRole
from app.models.intern_profile import InternProfile
from app.models.user import User
from app.schemas.intern import InternProfileCreateRequest, InternProfileResponse
from app.services.audit_service import record_audit_log

router = APIRouter(prefix="/candidates", tags=["Candidate Portal"])


@router.post(
    "/profile",
    response_model=InternProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_intern_profile(
    payload: InternProfileCreateRequest,
    request: Request,
    current_user: User = Depends(require_roles([UserRole.CANDIDATE])),
    db: AsyncSession = Depends(get_db_session),
) -> InternProfileResponse:
    existing = (
        await db.execute(
            select(InternProfile).where(InternProfile.user_id == current_user.user_id)
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Intern profile has already been submitted for this account.",
        )

    profile = InternProfile(
        user_id=current_user.user_id,
        full_name=payload.full_name.strip(),
        phone_number=payload.phone_number.strip(),
        college_name=payload.college_name.strip(),
        internship_role=payload.internship_role.strip(),
        start_date=payload.start_date,
        end_date=payload.end_date,
        address=(payload.address or "Sector V, Salt Lake").strip(),
        city=(payload.city or "Kolkata").strip(),
        state=(payload.state or "West Bengal").strip(),
        pin_code=(payload.pin_code or "700091").strip(),
        work_mode=(payload.work_mode or "Remote").strip(),
        work_schedule=(payload.work_schedule or "Monday to Friday (10:00 AM - 6:00 PM IST)").strip(),
        reporting_manager=(payload.reporting_manager or "Technical Project Manager, CREYOTECH").strip(),
        application_status=ApplicationStatus.SUBMITTED.value,
    )
    db.add(profile)
    await db.flush()

    await record_audit_log(
        db,
        actor_id=current_user.user_id,
        action="INTERN_PROFILE_SUBMITTED",
        target_entity=f"intern_profiles:{profile.profile_id}",
        ip_address=get_client_ip(request),
        details={
            "internship_role": profile.internship_role,
            "college_name": profile.college_name,
            "city": profile.city,
            "application_status": profile.application_status,
        },
    )
    await db.commit()
    await db.refresh(profile)
    return InternProfileResponse.model_validate(profile)


@router.get("/profile/me", response_model=InternProfileResponse)
async def get_my_intern_profile(
    current_user: User = Depends(require_roles([UserRole.CANDIDATE])),
    db: AsyncSession = Depends(get_db_session),
) -> InternProfileResponse:
    profile = (
        await db.execute(
            select(InternProfile).where(InternProfile.user_id == current_user.user_id)
        )
    ).scalar_one_or_none()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No intern profile found. Please submit your application details first.",
        )
    return InternProfileResponse.model_validate(profile)