"""add_certificate_verification_fields

Revision ID: 0002_cert_verification
Revises: 0001_initial
Create Date: 2026-10-26 10:00:00.000000

"""
from typing import Sequence, Union
import secrets
from alembic import op
import sqlalchemy as sa

revision: str = "0002_cert_verification"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"


def _gen_code() -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(12))


def upgrade() -> None:
    # 1. Add columns (verification_code initially nullable so existing rows can be backfilled)
    op.add_column("documents", sa.Column("verification_code", sa.String(length=12), nullable=True))
    op.add_column("documents", sa.Column("issuer_remarks", sa.Text(), nullable=True))
    op.add_column(
        "documents",
        sa.Column("is_valid", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )

    # 2. Backfill any existing documents with unique 12-char alphanumeric codes
    bind = op.get_bind()
    existing_docs = bind.execute(
        sa.text("SELECT document_id FROM documents WHERE verification_code IS NULL")
    ).fetchall()
    for row in existing_docs:
        code = _gen_code()
        bind.execute(
            sa.text(
                "UPDATE documents SET verification_code = :code, "
                "issuer_remarks = COALESCE(issuer_remarks, 'Verified and issued in good standing.') "
                "WHERE document_id = :doc_id"
            ),
            {"code": code, "doc_id": row[0]},
        )

    # 3. Enforce NOT NULL and create unique index
    op.alter_column("documents", "verification_code", existing_type=sa.String(length=12), nullable=False)
    op.create_index(
        "idx_documents_verification_code",
        "documents",
        ["verification_code"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("idx_documents_verification_code", table_name="documents")
    op.drop_column("documents", "is_valid")
    op.drop_column("documents", "issuer_remarks")
    op.drop_column("documents", "verification_code")