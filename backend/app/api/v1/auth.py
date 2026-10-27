import uuid
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db_session
from app.core.middleware import get_client_ip
from app.core.security import (
    REFRESH_COOKIE_NAME,
    clear_auth_cookies,
    create_access_token,
    create_refresh_token,
    decode_jwt_token,
    get_password_hash,
    set_auth_cookies,
    verify_password,
)
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.auth import (
    AuthStatusResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.services.audit_service import record_audit_log

router = APIRouter(prefix="/auth", tags=["Authentication & RBAC"])


@router.post(
    "/register",
    response_model=AuthStatusResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_candidate(
    payload: UserRegisterRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db_session),
) -> AuthStatusResponse:
    normalized_email = payload.email.lower().strip()
    existing = (
        await db.execute(select(User).where(User.email == normalized_email))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    user = User(
        email=normalized_email,
        password_hash=get_password_hash(payload.password),
        role=UserRole.CANDIDATE.value,
        is_active=True,
    )
    db.add(user)
    await db.flush()

    await record_audit_log(
        db,
        actor_id=user.user_id,
        action="USER_REGISTERED",
        target_entity=f"users:{user.user_id}",
        ip_address=get_client_ip(request),
        details={"email": user.email, "role": user.role},
    )
    await db.commit()
    await db.refresh(user)

    access_token = create_access_token(subject=user.user_id, role=user.role)
    refresh_token = create_refresh_token(subject=user.user_id, role=user.role)
    set_auth_cookies(response, access_token, refresh_token)

    return AuthStatusResponse(
        message="Candidate registered and authenticated successfully.",
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=AuthStatusResponse)
async def login(
    payload: UserLoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db_session),
) -> AuthStatusResponse:
    normalized_email = payload.email.lower().strip()
    user = (
        await db.execute(select(User).where(User.email == normalized_email))
    ).scalar_one_or_none()

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled.",
        )

    await record_audit_log(
        db,
        actor_id=user.user_id,
        action="USER_LOGIN",
        target_entity=f"users:{user.user_id}",
        ip_address=get_client_ip(request),
        details={"role": user.role},
    )
    await db.commit()

    access_token = create_access_token(subject=user.user_id, role=user.role)
    refresh_token = create_refresh_token(subject=user.user_id, role=user.role)
    set_auth_cookies(response, access_token, refresh_token)

    return AuthStatusResponse(
        message="Login successful.",
        user=UserResponse.model_validate(user),
    )


@router.post("/refresh", response_model=AuthStatusResponse)
async def refresh_access_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db_session),
) -> AuthStatusResponse:
    refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing refresh token cookie.",
        )
    try:
        payload = decode_jwt_token(refresh_token)
        if payload.get("type") != "refresh":
            raise ValueError("Invalid token type")
        user_uuid = uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, ValueError, KeyError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
        ) from exc

    user = (
        await db.execute(select(User).where(User.user_id == user_uuid))
    ).scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive.",
        )

    new_access = create_access_token(subject=user.user_id, role=user.role)
    new_refresh = create_refresh_token(subject=user.user_id, role=user.role)
    set_auth_cookies(response, new_access, new_refresh)

    return AuthStatusResponse(
        message="Access token refreshed.",
        user=UserResponse.model_validate(user),
    )


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    await record_audit_log(
        db,
        actor_id=current_user.user_id,
        action="USER_LOGOUT",
        target_entity=f"users:{current_user.user_id}",
        ip_address=get_client_ip(request),
        details={},
    )
    await db.commit()
    clear_auth_cookies(response)
    return {"message": "Logged out successfully."}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(current_user)