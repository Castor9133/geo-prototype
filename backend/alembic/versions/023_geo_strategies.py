"""GEO strategies + task/snapshot strategy_id

Revision ID: 023_geo_strategies
Revises: 022_geo_kb_workflow
Create Date: 2026-08-03
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "023_geo_strategies"
down_revision = "022_geo_kb_workflow"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "geo_strategies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("platform", sa.String(40), nullable=False),
        sa.Column("question_class", sa.String(200), nullable=False),
        sa.Column("query_variants", postgresql.JSONB(), nullable=True),
        sa.Column("content_orientation", sa.Text(), nullable=False, server_default=""),
        sa.Column("channel_matrix", postgresql.JSONB(), nullable=True),
        sa.Column("success_signal", postgresql.JSONB(), nullable=True),
        sa.Column("knowledge_document_ids", postgresql.JSONB(), nullable=True),
        sa.Column("knowledge_tag_pack", postgresql.JSONB(), nullable=True),
        sa.Column("knowledge_base_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("geo_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("parent_strategy_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(40), nullable=False, server_default="draft"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("site_url", sa.String(500), nullable=True),
        sa.Column("media_channel_type", sa.String(40), nullable=True),
        sa.Column("media_url", sa.String(500), nullable=True),
        sa.Column("deployed_at", sa.DateTime(), nullable=True),
        sa.Column("deployed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("verdict", sa.String(40), nullable=True),
        sa.Column("verdict_detail", postgresql.JSONB(), nullable=True),
        sa.Column("judged_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("judged_at", sa.DateTime(), nullable=True),
        sa.Column("force_reason", sa.Text(), nullable=True),
        sa.Column("force_initiated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("force_business_confirmed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("force_admin_confirmed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("force_status", sa.String(40), nullable=True),
        sa.Column("promote_suggestion", sa.String(40), nullable=True),
        sa.Column("promoted_document_ids", postgresql.JSONB(), nullable=True),
        sa.Column("gap_note", sa.Text(), nullable=True),
        sa.Column("meta", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["parent_strategy_id"], ["geo_strategies.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_geo_strategies_platform", "geo_strategies", ["platform"])
    op.create_index("ix_geo_strategies_question_class", "geo_strategies", ["question_class"])
    op.create_index("ix_geo_strategies_status", "geo_strategies", ["status"])
    op.create_index("ix_geo_strategies_kb", "geo_strategies", ["knowledge_base_id"])
    op.create_index("ix_geo_strategies_run", "geo_strategies", ["geo_run_id"])
    op.create_index("ix_geo_strategies_parent", "geo_strategies", ["parent_strategy_id"])
    op.create_index("ix_geo_strategies_created_by", "geo_strategies", ["created_by"])
    op.create_index("ix_geo_strategies_created_at", "geo_strategies", ["created_at"])

    op.add_column(
        "ce_content_tasks",
        sa.Column("strategy_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_ce_content_tasks_strategy_id", "ce_content_tasks", ["strategy_id"])

    op.add_column(
        "real_obs_snapshots",
        sa.Column("strategy_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_real_obs_snapshots_strategy_id", "real_obs_snapshots", ["strategy_id"])


def downgrade() -> None:
    op.drop_index("ix_real_obs_snapshots_strategy_id", table_name="real_obs_snapshots")
    op.drop_column("real_obs_snapshots", "strategy_id")
    op.drop_index("ix_ce_content_tasks_strategy_id", table_name="ce_content_tasks")
    op.drop_column("ce_content_tasks", "strategy_id")
    op.drop_index("ix_geo_strategies_created_at", table_name="geo_strategies")
    op.drop_index("ix_geo_strategies_created_by", table_name="geo_strategies")
    op.drop_index("ix_geo_strategies_parent", table_name="geo_strategies")
    op.drop_index("ix_geo_strategies_run", table_name="geo_strategies")
    op.drop_index("ix_geo_strategies_kb", table_name="geo_strategies")
    op.drop_index("ix_geo_strategies_status", table_name="geo_strategies")
    op.drop_index("ix_geo_strategies_question_class", table_name="geo_strategies")
    op.drop_index("ix_geo_strategies_platform", table_name="geo_strategies")
    op.drop_table("geo_strategies")
