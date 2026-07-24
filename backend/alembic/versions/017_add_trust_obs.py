"""增加可信观测探针 / 运行 / 样本表

Revision ID: 017_add_trust_obs
Revises: 016_merge_platform_iterations
Create Date: 2026-07-24
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "017_add_trust_obs"
down_revision = "016_merge_platform_iterations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "trust_obs_probes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("probe_key", sa.String(length=40), nullable=False),
        sa.Column("prompt_version", sa.String(length=40), nullable=False, server_default="probe-v1"),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("entity_name", sa.String(length=200), nullable=False, server_default="GEO 示范栏目"),
        sa.Column("entity_aliases", postgresql.JSONB(), nullable=True),
        sa.Column("owned_domains", postgresql.JSONB(), nullable=True),
        sa.Column("competitor_names", postgresql.JSONB(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_trust_obs_probes_probe_key", "trust_obs_probes", ["probe_key"], unique=True)
    op.create_index("ix_trust_obs_probes_prompt_version", "trust_obs_probes", ["prompt_version"])

    op.create_table(
        "trust_obs_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="pending"),
        sa.Column("prompt_version", sa.String(length=40), nullable=False, server_default="probe-v1"),
        sa.Column("locale", sa.String(length=40), nullable=False, server_default="zh-CN"),
        sa.Column("device", sa.String(length=40), nullable=False, server_default="api"),
        sa.Column("login_state", sa.String(length=40), nullable=False, server_default="api-key"),
        sa.Column("model_name", sa.String(length=120), nullable=True),
        sa.Column("repeats", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("aggregate", postgresql.JSONB(), nullable=True),
        sa.Column("method_note", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_trust_obs_runs_status", "trust_obs_runs", ["status"])
    op.create_index("ix_trust_obs_runs_created_by", "trust_obs_runs", ["created_by"])
    op.create_index("ix_trust_obs_runs_created_at", "trust_obs_runs", ["created_at"])

    op.create_table(
        "trust_obs_samples",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("probe_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("probe_key", sa.String(length=40), nullable=False),
        sa.Column("sample_index", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("raw_answer", sa.Text(), nullable=True),
        sa.Column("primary_label", sa.String(length=40), nullable=False, server_default="absent"),
        sa.Column("labels", postgresql.JSONB(), nullable=True),
        sa.Column("classifier_meta", postgresql.JSONB(), nullable=True),
        sa.Column("manual_override", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_trust_obs_samples_run_id", "trust_obs_samples", ["run_id"])
    op.create_index("ix_trust_obs_samples_probe_id", "trust_obs_samples", ["probe_id"])
    op.create_index("ix_trust_obs_samples_probe_key", "trust_obs_samples", ["probe_key"])
    op.create_index("ix_trust_obs_samples_primary_label", "trust_obs_samples", ["primary_label"])


def downgrade() -> None:
    op.drop_index("ix_trust_obs_samples_primary_label", table_name="trust_obs_samples")
    op.drop_index("ix_trust_obs_samples_probe_key", table_name="trust_obs_samples")
    op.drop_index("ix_trust_obs_samples_probe_id", table_name="trust_obs_samples")
    op.drop_index("ix_trust_obs_samples_run_id", table_name="trust_obs_samples")
    op.drop_table("trust_obs_samples")
    op.drop_index("ix_trust_obs_runs_created_at", table_name="trust_obs_runs")
    op.drop_index("ix_trust_obs_runs_created_by", table_name="trust_obs_runs")
    op.drop_index("ix_trust_obs_runs_status", table_name="trust_obs_runs")
    op.drop_table("trust_obs_runs")
    op.drop_index("ix_trust_obs_probes_prompt_version", table_name="trust_obs_probes")
    op.drop_index("ix_trust_obs_probes_probe_key", table_name="trust_obs_probes")
    op.drop_table("trust_obs_probes")
