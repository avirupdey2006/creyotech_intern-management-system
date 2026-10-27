import time
import uuid
from dataclasses import dataclass
from typing import Dict
import httpx
from fastapi import HTTPException, status

from app.core.config import settings
from app.core.encryption import crypto_engine
from app.core.logging import pino_logger, trigger_sentry_alert


@dataclass
class PendingKYCSession:
    """
    Holds ephemeral OTP session metadata in memory.
    Notice: Only the one-way cryptographic transaction_reference hash is retained.
    Raw government ID digits are NEVER stored in this struct (Section 5.1).
    """
    session_token: str
    profile_id: str
    id_type: str
    gateway_provider: str
    transaction_reference: str
    expires_at: float


class KYCGatewayService:
    """Third-Party KYC Identity Verification Gateway (Cashfree / Signzy / SurePass / Mock)."""

    def __init__(self) -> None:
        self._sessions: Dict[str, PendingKYCSession] = {}

    def _cleanup_expired(self) -> None:
        now = time.time()
        expired = [k for k, v in self._sessions.items() if v.expires_at < now]
        for k in expired:
            self._sessions.pop(k, None)

    async def initiate_otp(
        self,
        *,
        profile_id: uuid.UUID,
        id_type: str,
        raw_id_number: str,
    ) -> PendingKYCSession:
        """
        Initiates an OTP request with the configured KYC gateway, computes the cryptographic
        transaction_reference hash in memory, and immediately discards raw_id_number.
        """
        self._cleanup_expired()
        provider = settings.KYC_PROVIDER.upper()
        cleaned_id = raw_id_number.strip().upper()

        # Basic structural validation before hashing
        if id_type == "AADHAAR":
            digits_only = cleaned_id.replace("-", "").replace(" ", "")
            if not ( len(digits_only) == 12 and digits_only.isdigit() ):
                del cleaned_id, raw_id_number
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Invalid Aadhaar format. Expected 12 digits.",
                )
            normalized_id = digits_only
            del digits_only
        elif id_type == "PAN":
            if len(cleaned_id) != 10 or not cleaned_id.isalnum():
                del cleaned_id, raw_id_number
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Invalid PAN format. Expected 10 alphanumeric characters.",
                )
            normalized_id = cleaned_id
        else:
            normalized_id = cleaned_id

        gateway_txn_id = f"gw_{uuid.uuid4().hex[:16]}"

        # If configured for live third-party HTTP gateway (Cashfree / Signzy / SurePass)
        if provider in {"CASHFREE", "SIGNZY", "SUREPASS"}:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(
                        f"{settings.KYC_API_BASE_URL}/offline-aadhaar/otp",
                        headers={
                            "x-client-id": settings.KYC_CLIENT_ID,
                            "x-client-secret": settings.KYC_CLIENT_SECRET,
                            "Content-Type": "application/json",
                        },
                        json={"aadhaar_number": normalized_id},
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    gateway_txn_id = str(data.get("ref_id") or gateway_txn_id)
            except Exception as exc:
                del normalized_id, cleaned_id, raw_id_number
                trigger_sentry_alert(
                    "Third-party KYC gateway OTP initiation failed",
                    level="error",
                    context={"provider": provider, "profile_id": str(profile_id), "error": str(exc)},
                )
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Unable to reach third-party KYC identity gateway.",
                ) from exc

        # Compute one-way HMAC-SHA256 transaction reference hash and immediately discard raw ID
        txn_hash = crypto_engine.hash_kyc_reference(
            profile_id=str(profile_id),
            provider=provider,
            raw_id_number=normalized_id,
            gateway_txn_id=gateway_txn_id,
        )
        del normalized_id, cleaned_id, raw_id_number

        session_token = f"kyc_sess_{uuid.uuid4().hex}"
        session = PendingKYCSession(
            session_token=session_token,
            profile_id=str(profile_id),
            id_type=id_type,
            gateway_provider=provider,
            transaction_reference=txn_hash,
            expires_at=time.time() + 300,
        )
        self._sessions[session_token] = session

        pino_logger.info(
            "KYC OTP session initiated (raw ID discarded from memory)",
            profile_id=str(profile_id),
            provider=provider,
            id_type=id_type,
            transaction_reference=txn_hash,
        )
        return session

    async def verify_otp(
        self,
        *,
        profile_id: uuid.UUID,
        session_token: str,
        otp: str,
    ) -> tuple[bool, PendingKYCSession]:
        """Validates the OTP token against the KYC session and returns (is_verified, session)."""
        self._cleanup_expired()
        session = self._sessions.get(session_token)
        if not session or session.profile_id != str(profile_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired KYC verification session token.",
            )

        # Pop session so a token can only be consumed once (idempotent protection)
        self._sessions.pop(session_token, None)

        provider = session.gateway_provider
        is_valid = False

        if provider == "MOCK":
            # Deterministic mock verification: 123456 succeeds
            is_valid = otp == "123456"
        else:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(
                        f"{settings.KYC_API_BASE_URL}/offline-aadhaar/verify",
                        headers={
                            "x-client-id": settings.KYC_CLIENT_ID,
                            "x-client-secret": settings.KYC_CLIENT_SECRET,
                            "Content-Type": "application/json",
                        },
                        json={"otp": otp, "ref_id": session.transaction_reference},
                    )
                    is_valid = resp.status_code == 200
            except Exception as exc:
                trigger_sentry_alert(
                    "Third-party KYC gateway OTP verification error",
                    level="error",
                    context={"provider": provider, "profile_id": str(profile_id), "error": str(exc)},
                )
                is_valid = False

        del otp
        if not is_valid:
            trigger_sentry_alert(
                "KYC OTP verification failed for candidate profile",
                level="warning",
                context={
                    "profile_id": str(profile_id),
                    "provider": provider,
                    "transaction_reference": session.transaction_reference,
                },
            )
        return is_valid, session


kyc_gateway_service = KYCGatewayService()