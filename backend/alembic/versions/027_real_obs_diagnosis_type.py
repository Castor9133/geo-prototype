"""real_obs_samples.diagnosis_type

Revision ID: 027_real_obs_diagnosis_type
Revises: 026_phone_hash_encrypt
Create Date: 2026-08-05
"""

from alembic import op
import sqlalchemy as sa

revision = "027_real_obs_diagnosis_type"
down_revision = "026_phone_hash_encrypt"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "real_obs_samples",
        sa.Column("diagnosis_type", sa.String(length=40), nullable=True),
    )
    op.create_index("ix_real_obs_samples_diagnosis_type", "real_obs_samples", ["diagnosis_type"])


def downgrade() -> None:
    op.drop_index("ix_real_obs_samples_diagnosis_type", table_name="real_obs_samples")
    op.drop_column("real_obs_samples", "diagnosis_type")
