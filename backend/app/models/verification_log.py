import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import VerificationStatus

if TYPE_CHECKING:
    from app.models.intern_profile import InternProfile


class VerificationLog(Base):
    __tablename__ = "verification_logs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('SUCCESS', 'FAILED', 'PENDING')",
            name="chk_verification_logs_status",
        ),
    )

    verification_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("intern_profiles.profile_id", ondelete="CASCADE"),
        nullable=False,
    )
    gateway_provider: Mapped[str] = mapped_column(String(100), nullable=False)
    # Cryptographic HMAC-SHA256 hash only; never stores raw ID numbers
    transaction_reference: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=VerificationStatus.PENDING.value
    )
    verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    intern_profile: Mapped["InternProfile"] = relationship(
        "InternProfile", back_populates="verification_logs"
    )