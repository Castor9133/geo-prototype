"""真实点名观测 real_obs_snapshots / real_obs_samples

Revision ID: 021_add_real_obs
Revises: 020_unpublish_yao_jingang
Create Date: 2026-08-03
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "021_add_real_obs"
down_revision = "020_unpublish_yao_jingang"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "real_obs_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("geo_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("geo_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("phase", sa.String(20), nullable=False, server_default="after"),
        sa.Column("prompt_pack_version", sa.String(80), nullable=False, server_default="manual-v1"),
        sa.Column("platforms", postgresql.JSONB(), nullable=True),
        sa.Column("questions", postgresql.JSONB(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("owned_domains", postgresql.JSONB(), nullable=True),
        sa.Column("fact_source_urls", postgresql.JSONB(), nullable=True),
        sa.Column("entity_aliases", postgresql.JSONB(), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("probe_after_at", sa.DateTime(), nullable=True),
        sa.Column("method_note", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_real_obs_snapshots_geo_run_id", "real_obs_snapshots", ["geo_run_id"])
    op.create_index("ix_real_obs_snapshots_phase", "real_obs_snapshots", ["phase"])
    op.create_index("ix_real_obs_snapshots_status", "real_obs_snapshots", ["status"])
    op.create_index("ix_real_obs_snapshots_created_at", "real_obs_snapshots", ["created_at"])

    op.create_table(
        "real_obs_samples",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "snapshot_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("real_obs_snapshots.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("geo_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question_id", sa.String(80), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("platform", sa.String(40), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("answer_text", sa.Text(), nullable=True),
        sa.Column("citations", postgresql.JSONB(), nullable=True),
        sa.Column("mention", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("competitor_mention", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("owned_citation", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("strong_adopted", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("hit_snippet", sa.Text(), nullable=True),
        sa.Column("label_source", sa.String(20), nullable=False, server_default="rule"),
        sa.Column("ok", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("raw_meta", postgresql.JSONB(), nullable=True),
        sa.Column("sampled_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint(
            "snapshot_id",
            "question_id",
            "platform",
            "attempt",
            name="uq_real_obs_sample_unit",
        ),
    )
    op.create_index("ix_real_obs_samples_snapshot_id", "real_obs_samples", ["snapshot_id"])
    op.create_index("ix_real_obs_samples_geo_run_id", "real_obs_samples", ["geo_run_id"])
    op.create_index("ix_real_obs_samples_question_id", "real_obs_samples", ["question_id"])
    op.create_index("ix_real_obs_samples_platform", "real_obs_samples", ["platform"])


def downgrade() -> None:
    op.drop_index("ix_real_obs_samples_platform", table_name="real_obs_samples")
    op.drop_index("ix_real_obs_samples_question_id", table_name="real_obs_samples")
    op.drop_index("ix_real_obs_samples_geo_run_id", table_name="real_obs_samples")
    op.drop_index("ix_real_obs_samples_snapshot_id", table_name="real_obs_samples")
    op.drop_table("real_obs_samples")
    op.drop_index("ix_real_obs_snapshots_created_at", table_name="real_obs_snapshots")
    op.drop_index("ix_real_obs_snapshots_status", table_name="real_obs_snapshots")
    op.drop_index("ix_real_obs_snapshots_phase", table_name="real_obs_snapshots")
    op.drop_index("ix_real_obs_snapshots_geo_run_id", table_name="real_obs_snapshots")
    op.drop_table("real_obs_snapshots")
