import uuid
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.core.database import AsyncSessionLocal
from app.core.security import (
    create_access_token,
    decode_jwt_token,
    get_password_hash,
    verify_password,
)
from app.main import app
from app.models.enums import UserRole


def test_bcrypt_and_jwt_primitives():
    raw_pwd = "SecurePass#2026"
    hashed = get_password_hash(raw_pwd)
    assert verify_password(raw_pwd, hashed) is True
    assert verify_password("WrongPass", hashed) is False

    token = create_access_token(subject="user-123", role=UserRole.HR_REVIEWER.value)
    decoded = decode_jwt_token(token)
    assert decoded["sub"] == "user-123"
    assert decoded["role"] == "HR_REVIEWER"
    assert decoded["type"] == "access"


async def test_httponly_samesite_strict_cookies_and_owasp_headers():
    email = f"auth.rbac.{uuid.uuid4().hex[:8]}@ims.test"
    user_id: uuid.UUID | None = None

    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            reg_resp = await client.post(
                "/api/v1/auth/register",
                json={"email": email, "password": "Candidate@2026!"},
            )
            assert reg_resp.status_code == 201
            user_id = uuid.UUID(reg_resp.json()["user"]["user_id"])

            # Verify OWASP Security Headers (Specification Section 3.1)
            assert "Strict-Transport-Security" in reg_resp.headers
            assert "Content-Security-Policy" in reg_resp.headers
            assert reg_resp.headers["X-Frame-Options"] == "DENY"
            assert reg_resp.headers["X-Content-Type-Options"] == "nosniff"

            # Verify HttpOnly, SameSite=Strict JWT cookies (Specification Section 3.3)
            cookies = reg_resp.headers.get_list("set-cookie")
            access_cookie = next(c for c in cookies if "ims_access_token=" in c)
            assert "HttpOnly" in access_cookie
            assert "SameSite=strict" in access_cookie

            # Candidate MUST be blocked (403 Forbidden) from HR/Admin endpoints
            hr_queue_resp = await client.get("/api/v1/admin/applications")
            assert hr_queue_resp.status_code == 403

            audit_resp = await client.get("/api/v1/admin/audit-logs")
            assert audit_resp.status_code == 403
    finally:
        if user_id:
            async with AsyncSessionLocal() as db:
                await db.execute(text("DELETE FROM audit_logs WHERE actor_id = :uid"), {"uid": user_id})
                await db.execute(text("DELETE FROM users WHERE user_id = :uid"), {"uid": user_id})
                await db.commit()


async def test_hr_reviewer_blocked_from_admin_only_audit_logs():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "hr.reviewer@ims.local", "password": "HrReviewer@IMS2026!"},
        )
        assert login_resp.status_code == 200

        # HR_REVIEWER can access application queue
        apps_resp = await client.get("/api/v1/admin/applications")
        assert apps_resp.status_code == 200

        # HR_REVIEWER cannot access ADMIN-only immutable audit trail endpoint
        audit_resp = await client.get("/api/v1/admin/audit-logs")
        assert audit_resp.status_code == 403