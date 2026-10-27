import uuid
from datetime import date, datetime
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ApplicationStatus, DocumentType


class StageDecisionRequest(BaseModel):
    target_status: Literal[
        "PROVISIONAL_APPROVED",
        "FINAL_APPROVED",
        "COMPLETED",
        "REJECTED",
    ]
    remarks: str = Field(
        default="Successfully satisfied all internship and evaluation criteria.",
        max_length=500,
    )
    # Optional HR/Admin overrides for Appointment & Certificate Generation
    internship_role: Optional[str] = Field(default=None, max_length=150)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    work_mode: Optional[str] = Field(default=None, max_length=50)
    work_schedule: Optional[str] = Field(default=None, max_length=150)
    reporting_manager: Optional[str] = Field(default=None, max_length=150)
    address: Optional[str] = Field(default=None, max_length=500)
    city: Optional[str] = Field(default=None, max_length=100)
    state: Optional[str] = Field(default=None, max_length=100)
    pin_code: Optional[str] = Field(default=None, max_length=20)


class DocumentMetadataResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    document_id: uuid.UUID
    profile_id: uuid.UUID
    document_type: DocumentType
    verification_code: str
    issuer_remarks: Optional[str] = None
    is_valid: bool = True
    checksum_sha256: str
    admin_approved_by: uuid.UUID
    generated_at: datetime


class StageDecisionResponse(BaseModel):
    message: str
    profile_id: uuid.UUID
    previous_status: ApplicationStatus
    new_status: ApplicationStatus
    idempotency_key: str
    document: DocumentMetadataResponse | None = None


class SignedUrlResponse(BaseModel):
    document_id: uuid.UUID
    document_type: DocumentType
    verification_code: str
    download_url: str
    expires_at: int
    checksum_sha256: str


class CertificateVerificationResponse(BaseModel):
    """Public response returned when an external verifier enters a 12-char verification code."""

    verified: bool
    validity_status: Literal["VALID", "REVOKED"]
    verification_code: str
    document_type: DocumentType
    intern_name: str
    internship_designation: str
    college_name: str
    start_date: date
    end_date: date
    duration_display: str
    work_mode: Optional[str] = None
    reporting_manager: Optional[str] = None
    issued_at: datetime
    issuer_remarks: Optional[str] = None
    checksum_sha256: str