"""add_creyotech_profile_fields

Revision ID: 0003_creyotech_fields
Revises: 0002_cert_verification
Create Date: 2026-10-26 14:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0003_creyotech_fields"
down_revision: Union[str, None] = "0002_cert_verification"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("intern_profiles", sa.Column("address", sa.Text(), nullable=True))
    op.add_column("intern_profiles", sa.Column("city", sa.String(length=100), nullable=True))
    op.add_column("intern_profiles", sa.Column("state", sa.String(length=100), nullable=True))
    op.add_column("intern_profiles", sa.Column("pin_code", sa.String(length=20), nullable=True))
    op.add_column("intern_profiles", sa.Column("work_mode", sa.String(length=50), nullable=True))
    op.add_column("intern_profiles", sa.Column("work_schedule", sa.String(length=150), nullable=True))
    op.add_column("intern_profiles", sa.Column("reporting_manager", sa.String(length=150), nullable=True))

    # Backfill existing profiles with sensible defaults
    op.execute(
        sa.text(
            "UPDATE intern_profiles SET "
            "address = COALESCE(address, 'Sector V, Salt Lake'), "
            "city = COALESCE(city, 'Kolkata'), "
            "state = COALESCE(state, 'West Bengal'), "
            "pin_code = COALESCE(pin_code, '700091'), "
            "work_mode = COALESCE(work_mode, 'Remote'), "
            "work_schedule = COALESCE(work_schedule, 'Monday to Friday (10:00 AM - 6:00 PM IST)'), "
            "reporting_manager = COALESCE(reporting_manager, 'Technical Project Manager, CREYOTECH')"
        )
    )


def downgrade() -> None:
    op.drop_column("intern_profiles", "reporting_manager")
    op.drop_column("intern_profiles", "work_schedule")
    op.drop_column("intern_profiles", "work_mode")
    op.drop_column("intern_profiles", "pin_code")
    op.drop_column("intern_profiles", "state")
    op.drop_column("intern_profiles", "city")
    op.drop_column("intern_profiles", "address")