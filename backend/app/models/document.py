import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.encryption import crypto_engine

if TYPE_CHECKING:
    from app.models.intern_profile import InternProfile
    from app.models.user import User


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint(
            "document_type IN ('PROVISIONAL_OFFER', 'FINAL_OFFER', 'COMPLETION_CERTIFICATE')",
            name="chk_documents_type",
        ),
        Index("idx_documents_profile", "profile_id"),
        Index("idx_documents_verification_code", "verification_code", unique=True),
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("intern_profiles.profile_id", ondelete="CASCADE"),
        nullable=False,
    )
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    verification_code: Mapped[str] = mapped_column(
        String(12),
        unique=True,
        nullable=False,
        default=lambda: crypto_engine.generate_verification_code(12),
    )
    issuer_remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_valid: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    admin_approved_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="RESTRICT"),
        nullable=False,
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    intern_profile: Mapped["InternProfile"] = relationship(
        "InternProfile", back_populates="documents"
    )
    approved_by_user: Mapped["User"] = relationship(
        "User", back_populates="approved_documents"
    )