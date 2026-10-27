"""initial_ims_schema

Revision ID: 0001_initial
Revises: 
Create Date: 2026-10-23 17:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. users table
    op.create_table(
        "users",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("role IN ('CANDIDATE', 'HR_REVIEWER', 'ADMIN')", name="chk_users_role"),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    # 2. intern_profiles table
    op.create_table(
        "intern_profiles",
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("phone_number", sa.Text(), nullable=False),
        sa.Column("college_name", sa.String(length=255), nullable=False),
        sa.Column("internship_role", sa.String(length=150), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("application_status", sa.String(length=50), nullable=False, server_default="SUBMITTED"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "application_status IN ('SUBMITTED', 'IDENTITY_VERIFIED', 'PROVISIONAL_APPROVED', 'FINAL_APPROVED', 'COMPLETED', 'REJECTED')",
            name="chk_intern_profiles_status",
        ),
        sa.CheckConstraint("end_date >= start_date", name="chk_intern_dates"),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("profile_id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("idx_profiles_status", "intern_profiles", ["application_status"], unique=False)

    # 3. verification_logs table
    op.create_table(
        "verification_logs",
        sa.Column("verification_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gateway_provider", sa.String(length=100), nullable=False),
        sa.Column("transaction_reference", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("status IN ('SUCCESS', 'FAILED', 'PENDING')", name="chk_verification_logs_status"),
        sa.ForeignKeyConstraint(["profile_id"], ["intern_profiles.profile_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("verification_id"),
        sa.UniqueConstraint("transaction_reference"),
    )

    # 4. documents table
    op.create_table(
        "documents",
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_type", sa.String(length=50), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("admin_approved_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "document_type IN ('PROVISIONAL_OFFER', 'FINAL_OFFER', 'COMPLETION_CERTIFICATE')",
            name="chk_documents_type",
        ),
        sa.ForeignKeyConstraint(["admin_approved_by"], ["users.user_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["profile_id"], ["intern_profiles.profile_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("document_id"),
    )
    op.create_index("idx_documents_profile", "documents", ["profile_id"], unique=False)

    # 5. audit_logs table
    op.create_table(
        "audit_logs",
        sa.Column("log_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(length=150), nullable=False),
        sa.Column("target_entity", sa.String(length=150), nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["users.user_id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("log_id"),
    )
    op.create_index("idx_audit_timestamp", "audit_logs", ["timestamp"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_audit_timestamp", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_index("idx_documents_profile", table_name="documents")
    op.drop_table("documents")
    op.drop_table("verification_logs")
    op.drop_index("idx_profiles_status", table_name="intern_profiles")
    op.drop_table("intern_profiles")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")