import uuid
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ApplicationStatus, VerificationStatus


class KYCInitiateOTPRequest(BaseModel):
    id_type: Literal["AADHAAR", "PAN", "PASSPORT"] = "AADHAAR"
    # Processed strictly in volatile memory over TLS; never persisted or logged (Section 3.4 & 5.1)
    id_number: str = Field(..., min_length=6, max_length=24)


class KYCInitiateOTPResponse(BaseModel):
    session_token: str
    gateway_provider: str
    masked_destination: str
    expires_in_seconds: int = 300
    message: str


class KYCVerifyOTPRequest(BaseModel):
    session_token: str = Field(..., min_length=10)
    otp: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")


class VerificationLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    verification_id: uuid.UUID
    profile_id: uuid.UUID
    gateway_provider: str
    transaction_reference: str
    status: VerificationStatus
    verified_at: datetime


class KYCVerifyOTPResponse(BaseModel):
    message: str
    application_status: ApplicationStatus
    verification: VerificationLogResponse