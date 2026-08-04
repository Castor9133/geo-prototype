"""strategy diagnostic + baseline/after snapshot ids

Revision ID: 024_strategy_diag_baseline
Revises: 023_geo_strategies
Create Date: 2026-08-03
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "024_strategy_diag_baseline"
down_revision = "023_geo_strategies"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "geo_strategies",
        sa.Column("diagnostic_report_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "geo_strategies",
        sa.Column("baseline_snapshot_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "geo_strategies",
        sa.Column("after_snapshot_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_geo_strategies_diag", "geo_strategies", ["diagnostic_report_id"])
    op.create_index("ix_geo_strategies_baseline", "geo_strategies", ["baseline_snapshot_id"])
    op.create_index("ix_geo_strategies_after", "geo_strategies", ["after_snapshot_id"])


def downgrade() -> None:
    op.drop_index("ix_geo_strategies_after", table_name="geo_strategies")
    op.drop_index("ix_geo_strategies_baseline", table_name="geo_strategies")
    op.drop_index("ix_geo_strategies_diag", table_name="geo_strategies")
    op.drop_column("geo_strategies", "after_snapshot_id")
    op.drop_column("geo_strategies", "baseline_snapshot_id")
    op.drop_column("geo_strategies", "diagnostic_report_id")
