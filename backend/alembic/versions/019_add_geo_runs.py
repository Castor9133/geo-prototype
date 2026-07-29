"""GEO 回合 geo_runs

Revision ID: 019_add_geo_runs
Revises: 018_add_content_engine
Create Date: 2026-07-29
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "019_add_geo_runs"
down_revision = "018_add_content_engine"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "geo_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("entity", sa.String(200), nullable=False),
        sa.Column("competitor", sa.String(200), nullable=False),
        sa.Column("url", sa.String(500), nullable=True),
        sa.Column("platforms", postgresql.JSONB(), nullable=True),
        sa.Column("status", sa.String(40), server_default="active"),
        sa.Column("artifacts", postgresql.JSONB(), nullable=True),
        sa.Column("observe_script_key", sa.String(120), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_geo_runs_status", "geo_runs", ["status"])
    op.create_index("ix_geo_runs_created_at", "geo_runs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_geo_runs_created_at", table_name="geo_runs")
    op.drop_index("ix_geo_runs_status", table_name="geo_runs")
    op.drop_table("geo_runs")
