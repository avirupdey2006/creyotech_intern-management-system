import uuid
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text

from app.core.database import AsyncSessionLocal
from app.core.encryption import crypto_engine
from app.main import app
from app.models import AuditLog, VerificationLog


def test_kyc_reference_hash_excludes_raw_digits():
    raw_id = "6543-2109-8765"
    digest = crypto_engine.hash_kyc_reference(
        profile_id=str(uuid.uuid4()),
        provider="MOCK",
        raw_id_number=raw_id,
        gateway_txn_id="gw_test_1",
    )
    assert len(digest) == 64
    assert "6543" not in digest
    assert "2109" not in digest
    assert "8765" not in digest


async def test_kyc_flow_persists_zero_raw_government_id_digits(capsys):
    email = f"kyc.min.{uuid.uuid4().hex[:8]}@ims.test"
    raw_aadhaar = "7654-3210-9876"
    raw_digits = "765432109876"
    raw_phone = "+919800112233"
    user_id: uuid.UUID | None = None
    profile_id: uuid.UUID | None = None

    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            reg = await client.post(
                "/api/v1/auth/register",
                json={"email": email, "password": "Candidate@2026!"},
            )
            user_id = uuid.UUID(reg.json()["user"]["user_id"])

            prof = await client.post(
                "/api/v1/candidates/profile",
                json={
                    "full_name": "Kabir Chatterjee",
                    "phone_number": raw_phone,
                    "college_name": "Guru Nanak Institute of Technology",
                    "internship_role": "Cybersecurity Analyst Intern",
                    "start_date": "2026-11-01",
                    "end_date": "2027-04-30",
                },
            )
            assert prof.status_code == 201
            profile_id = uuid.UUID(prof.json()["profile_id"])

            # Verify phone_number is encrypted at rest in PostgreSQL (Section 5.2)
            async with AsyncSessionLocal() as db:
                stored_cipher = (
                    await db.execute(
                        text("SELECT phone_number FROM intern_profiles WHERE profile_id = :pid"),
                        {"pid": profile_id},
                    )
                ).scalar_one()
                assert stored_cipher != raw_phone
                assert "9800112233" not in stored_cipher

            # Initiate & Verify KYC OTP
            init_resp = await client.post(
                "/api/v1/kyc/initiate-otp",
                json={"id_type": "AADHAAR", "id_number": raw_aadhaar},
            )
            assert init_resp.status_code == 200
            session_token = init_resp.json()["session_token"]

            ver_resp = await client.post(
                "/api/v1/kyc/verify-otp",
                json={"session_token": session_token, "otp": "123456"},
            )
            assert ver_resp.status_code == 200
            assert ver_resp.json()["application_status"] == "IDENTITY_VERIFIED"

            # Inspect DB tables & Pino stdout logs for zero raw ID leakage
            async with AsyncSessionLocal() as db:
                vlog = (
                    await db.execute(
                        select(VerificationLog).where(VerificationLog.profile_id == profile_id)
                    )
                ).scalar_one()
                assert raw_aadhaar not in vlog.transaction_reference
                assert raw_digits not in vlog.transaction_reference

                audits = (
                    await db.execute(select(AuditLog).where(AuditLog.actor_id == user_id))
                ).scalars().all()
                for entry in audits:
                    dump = str(entry.details)
                    assert raw_aadhaar not in dump
                    assert raw_digits not in dump

            stdout_logs = capsys.readouterr().out
            assert raw_aadhaar not in stdout_logs
            assert raw_digits not in stdout_logs
    finally:
        if user_id:
            async with AsyncSessionLocal() as db:
                await db.execute(text("DELETE FROM audit_logs WHERE actor_id = :uid"), {"uid": user_id})
                await db.execute(text("DELETE FROM users WHERE user_id = :uid"), {"uid": user_id})
                await db.commit()