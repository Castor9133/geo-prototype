"""GEO KB tiers/tags + task workflow + user geo_role

Revision ID: 022_geo_kb_workflow
Revises: 021_add_real_obs
Create Date: 2026-08-03
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "022_geo_kb_workflow"
down_revision = "021_add_real_obs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("geo_role", sa.String(40), nullable=True))
    op.create_index("ix_users_geo_role", "users", ["geo_role"])

    op.add_column("ce_knowledge_documents", sa.Column("tier", sa.String(10), server_default="L2"))
    op.add_column("ce_knowledge_documents", sa.Column("tags", postgresql.JSONB(), nullable=True))
    op.add_column(
        "ce_knowledge_documents",
        sa.Column("review_state", sa.String(40), server_default="approved"),
    )
    op.add_column("ce_knowledge_documents", sa.Column("fact_cards", postgresql.JSONB(), nullable=True))
    op.add_column("ce_knowledge_documents", sa.Column("external_approved_at", sa.DateTime(), nullable=True))
    op.add_column("ce_knowledge_documents", sa.Column("local_confirmed_at", sa.DateTime(), nullable=True))
    op.add_column(
        "ce_knowledge_documents",
        sa.Column("local_confirmed_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "ce_knowledge_documents",
        sa.Column("submitted_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column("ce_knowledge_documents", sa.Column("external_id", sa.String(120), nullable=True))
    op.create_index("ix_ce_knowledge_documents_tier", "ce_knowledge_documents", ["tier"])
    op.create_index("ix_ce_knowledge_documents_review_state", "ce_knowledge_documents", ["review_state"])

    op.add_column(
        "ce_content_tasks",
        sa.Column("workflow_status", sa.String(40), server_default="claimed"),
    )
    op.add_column("ce_content_tasks", sa.Column("template_draft_body", sa.Text(), nullable=True))
    op.add_column("ce_content_tasks", sa.Column("channel_draft_body", sa.Text(), nullable=True))
    op.add_column("ce_content_tasks", sa.Column("channel_key", sa.String(120), nullable=True))
    op.add_column(
        "ce_content_tasks",
        sa.Column("claimed_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "ce_content_tasks",
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "ce_content_tasks",
        sa.Column("geo_run_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "ce_content_tasks",
        sa.Column("promote_suggestion", sa.String(40), nullable=True),
    )
    op.add_column(
        "ce_content_tasks",
        sa.Column("promoted_document_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_ce_content_tasks_workflow_status", "ce_content_tasks", ["workflow_status"])
    op.create_index("ix_ce_content_tasks_geo_run_id", "ce_content_tasks", ["geo_run_id"])


def downgrade() -> None:
    op.drop_index("ix_ce_content_tasks_geo_run_id", table_name="ce_content_tasks")
    op.drop_index("ix_ce_content_tasks_workflow_status", table_name="ce_content_tasks")
    for col in (
        "promoted_document_id",
        "promote_suggestion",
        "geo_run_id",
        "reviewed_by",
        "claimed_by",
        "channel_key",
        "channel_draft_body",
        "template_draft_body",
        "workflow_status",
    ):
        op.drop_column("ce_content_tasks", col)

    op.drop_index("ix_ce_knowledge_documents_review_state", table_name="ce_knowledge_documents")
    op.drop_index("ix_ce_knowledge_documents_tier", table_name="ce_knowledge_documents")
    for col in (
        "external_id",
        "submitted_by",
        "local_confirmed_by",
        "local_confirmed_at",
        "external_approved_at",
        "fact_cards",
        "review_state",
        "tags",
        "tier",
    ):
        op.drop_column("ce_knowledge_documents", col)

    op.drop_index("ix_users_geo_role", table_name="users")
    op.drop_column("users", "geo_role")
