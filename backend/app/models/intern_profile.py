import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.encryption import EncryptedString
from app.models.enums import ApplicationStatus

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.verification_log import VerificationLog
    from app.models.document import Document


class InternProfile(Base):
    __tablename__ = "intern_profiles"
    __table_args__ = (
        CheckConstraint(
            "application_status IN ('SUBMITTED', 'IDENTITY_VERIFIED', 'PROVISIONAL_APPROVED', 'FINAL_APPROVED', 'COMPLETED', 'REJECTED')",
            name="chk_intern_profiles_status",
        ),
        CheckConstraint("end_date >= start_date", name="chk_intern_dates"),
        Index("idx_profiles_status", "application_status"),
    )

    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Encrypted at rest using Fernet (Section 5.2 Encryption Standards)
    phone_number: Mapped[str] = mapped_column(EncryptedString, nullable=False)
    college_name: Mapped[str] = mapped_column(String(255), nullable=False)
    internship_role: Mapped[str] = mapped_column(String(150), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Address & HR Appointment Metadata for CREYOTECH Offer Letters & Certificates
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default="Sector V, Salt Lake")
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, default="Kolkata")
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, default="West Bengal")
    pin_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, default="700091")
    work_mode: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, default="Remote")
    work_schedule: Mapped[Optional[str]] = mapped_column(
        String(150), nullable=True, default="Monday to Friday (Flexible Hours)"
    )
    reporting_manager: Mapped[Optional[str]] = mapped_column(
        String(150), nullable=True, default="Project Lead — Engineering, CREYOTECH"
    )

    application_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=ApplicationStatus.SUBMITTED.value
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="intern_profile")
    verification_logs: Mapped[List["VerificationLog"]] = relationship(
        "VerificationLog", back_populates="intern_profile", cascade="all, delete-orphan"
    )
    documents: Mapped[List["Document"]] = relationship(
        "Document", back_populates="intern_profile", cascade="all, delete-orphan"
    )