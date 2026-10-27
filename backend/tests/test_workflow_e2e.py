from pathlib import Path
import uuid
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text

from app.core.database import AsyncSessionLocal
from app.core.encryption import crypto_engine
from app.main import app
from app.models import Document
from app.services.email_dispatcher import email_dispatcher_service


async def test_complete_5_stage_onboarding_workflow_e2e():
    candidate_email = f"e2e.intern.{uuid.uuid4().hex[:8]}@ims.test"
    created_files: list[Path] = []
    candidate_user_id: uuid.UUID | None = None
    profile_id: uuid.UUID | None = None

    transport = ASGITransport(app=app)
    try:
        # 1. Candidate Register, Submit Profile & Verify KYC
        async with AsyncClient(transport=transport, base_url="http://testserver") as cand:
            reg = await cand.post(
                "/api/v1/auth/register",
                json={"email": candidate_email, "password": "Candidate@2026!"},
            )
            assert reg.status_code == 201
            candidate_user_id = uuid.UUID(reg.json()["user"]["user_id"])

            prof = await cand.post(
                "/api/v1/candidates/profile",
                json={
                    "full_name": "Ananya Roy",
                    "phone_number": "+919831122334",
                    "college_name": "Guru Nanak Institute of Technology",
                    "internship_role": "Backend & Distributed Systems Intern",
                    "start_date": "2026-11-01",
                    "end_date": "2027-04-30",
                },
            )
            assert prof.status_code == 201
            profile_id = uuid.UUID(prof.json()["profile_id"])

            otp_init = await cand.post(
                "/api/v1/kyc/initiate-otp",
                json={"id_type": "AADHAAR", "id_number": "2345-6789-0123"},
            )
            sess_token = otp_init.json()["session_token"]

            otp_ver = await cand.post(
                "/api/v1/kyc/verify-otp",
                json={"session_token": sess_token, "otp": "123456"},
            )
            assert otp_ver.status_code == 200
            assert otp_ver.json()["application_status"] == "IDENTITY_VERIFIED"

        # 2. HR Reviewer Approves PROVISIONAL_APPROVED -> PROVISIONAL_OFFER
        async with AsyncClient(transport=transport, base_url="http://testserver") as hr:
            await hr.post(
                "/api/v1/auth/login",
                json={"email": "hr.reviewer@ims.local", "password": "HrReviewer@IMS2026!"},
            )
            prov = await hr.post(
                f"/api/v1/admin/applications/{profile_id}/decision",
                json={"target_status": "PROVISIONAL_APPROVED", "remarks": "HR Approved"},
            )
            assert prov.status_code == 200
            assert prov.json()["document"]["document_type"] == "PROVISIONAL_OFFER"

        # 3. Admin Approves FINAL_APPROVED and COMPLETED + Idempotency Check
        async with AsyncClient(transport=transport, base_url="http://testserver") as admin:
            await admin.post(
                "/api/v1/auth/login",
                json={"email": "admin@ims.local", "password": "Admin@IMS2026!"},
            )
            fin = await admin.post(
                f"/api/v1/admin/applications/{profile_id}/decision",
                json={"target_status": "FINAL_APPROVED", "remarks": "Admin Final Approval"},
            )
            assert fin.status_code == 200
            assert fin.json()["document"]["document_type"] == "FINAL_OFFER"

            comp = await admin.post(
                f"/api/v1/admin/applications/{profile_id}/decision",
                json={"target_status": "COMPLETED", "remarks": "Internship Completed"},
            )
            assert comp.status_code == 200
            comp_doc_id = comp.json()["document"]["document_id"]

            # Idempotent retry check (Section 5.3)
            count_before = email_dispatcher_service.get_today_count()
            retry = await admin.post(
                f"/api/v1/admin/applications/{profile_id}/decision",
                json={"target_status": "COMPLETED", "remarks": "Idempotent retry"},
            )
            assert retry.status_code == 200
            assert retry.json()["document"]["document_id"] == comp_doc_id
            assert email_dispatcher_service.get_today_count() == count_before

        # 4. Candidate Downloads Decrypted PDF via Signed URL
        async with AsyncSessionLocal() as db:
            docs = (
                await db.execute(select(Document).where(Document.profile_id == profile_id))
            ).scalars().all()
            assert len(docs) == 3
            for d in docs:
                p = Path(d.storage_path)
                created_files.append(p)
                assert p.exists()
                assert not p.read_bytes().startswith(b"%PDF")

        async with AsyncClient(transport=transport, base_url="http://testserver") as cand:
            await cand.post(
                "/api/v1/auth/login",
                json={"email": candidate_email, "password": "Candidate@2026!"},
            )
            my_docs = (await cand.get("/api/v1/documents/my")).json()
            assert len(my_docs) == 3

            doc_id = my_docs[0]["document_id"]
            expected_sha = my_docs[0]["checksum_sha256"]
            signed = (await cand.post(f"/api/v1/documents/{doc_id}/signed-url")).json()
            dl = await cand.get(signed["download_url"])
            assert dl.status_code == 200
            assert dl.content.startswith(b"%PDF-")
            assert crypto_engine.sha256_checksum(dl.content) == expected_sha
    finally:
        for f in created_files:
            f.unlink(missing_ok=True)
        if candidate_user_id and profile_id:
            async with AsyncSessionLocal() as db:
                await db.execute(text("DELETE FROM documents WHERE profile_id = :pid"), {"pid": profile_id})
                await db.execute(text("DELETE FROM audit_logs WHERE actor_id = :uid"), {"uid": candidate_user_id})
                await db.execute(text("DELETE FROM users WHERE user_id = :uid"), {"uid": candidate_user_id})
                await db.commit()