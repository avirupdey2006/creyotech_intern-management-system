import uuid
from typing import Callable, Sequence
import jwt
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.logging import trigger_sentry_alert
from app.core.security import ACCESS_COOKIE_NAME, decode_jwt_token
from app.models.enums import UserRole
from app.models.user import User


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> User:
    token = request.cookies.get(ACCESS_COOKIE_NAME)
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.removeprefix("Bearer ").strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Missing access token cookie.",
        )

    try:
        payload = decode_jwt_token(token)
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type.",
            )
        user_id_str = payload.get("sub")
        user_uuid = uuid.UUID(user_id_str)
    except (jwt.PyJWTError, ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
        ) from exc

    stmt = select(User).where(User.user_id == user_uuid)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive or no longer exists.",
        )
    return user


def require_roles(allowed_roles: Sequence[UserRole | str]) -> Callable:
    allowed_set = {r.value if isinstance(r, UserRole) else str(r) for r in allowed_roles}

    async def _role_checker(
        request: Request,
        current_user: User = Depends(get_current_user),
    ) -> User:
        if current_user.role not in allowed_set:
            trigger_sentry_alert(
                "RBAC authorization violation detected",
                level="warning",
                context={
                    "user_id": str(current_user.user_id),
                    "user_role": current_user.role,
                    "required_roles": list(allowed_set),
                    "path": request.url.path,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role(s): {', '.join(sorted(allowed_set))}",
            )
        return current_user

    return _role_checker