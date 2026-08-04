"""white-hat observation account pool

Revision ID: 025_obs_white_accounts
Revises: 024_strategy_diag_baseline
Create Date: 2026-08-04
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "025_obs_white_accounts"
down_revision = "024_strategy_diag_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "obs_white_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("platform", sa.String(40), nullable=False, index=True),
        sa.Column("label", sa.String(120), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="available", index=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("meta", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("platform", "label", name="uq_obs_white_platform_label"),
    )


def downgrade() -> None:
    op.drop_table("obs_white_accounts")
