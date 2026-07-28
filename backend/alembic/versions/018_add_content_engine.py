"""内容引擎 M1：知识库 / 切片 / 提示词 / 任务 / 渠道

Revision ID: 018_add_content_engine
Revises: 017_add_trust_obs
Create Date: 2026-07-28
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "018_add_content_engine"
down_revision = "017_add_trust_obs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ce_knowledge_bases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source_label", sa.String(120), nullable=True),
        sa.Column("meta", postgresql.JSONB(), nullable=True),
        sa.Column("doc_count", sa.Integer(), server_default="0"),
        sa.Column("chunk_count", sa.Integer(), server_default="0"),
        sa.Column("vectorized_count", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_ce_kb_slug", "ce_knowledge_bases", ["slug"], unique=True)

    op.create_table(
        "ce_knowledge_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("knowledge_base_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ce_knowledge_bases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("source_path", sa.String(500), nullable=True),
        sa.Column("source_url", sa.String(500), nullable=True),
        sa.Column("status", sa.String(40), server_default="ready"),
        sa.Column("chunk_count", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_ce_docs_kb", "ce_knowledge_documents", ["knowledge_base_id"])

    op.create_table(
        "ce_knowledge_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("knowledge_base_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_index", sa.Integer(), server_default="0"),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", postgresql.JSONB(), nullable=True),
        sa.Column("token_estimate", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_ce_chunks_kb", "ce_knowledge_chunks", ["knowledge_base_id"])
    op.create_index("ix_ce_chunks_doc", "ce_knowledge_chunks", ["document_id"])

    op.create_table(
        "ce_content_prompts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("locale", sa.String(20), server_default="zh-CN"),
        sa.Column("kind", sa.String(40), server_default="content"),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), server_default="100"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "ce_content_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("knowledge_base_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("prompt_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("channel_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("template_key", sa.String(120), nullable=True),
        sa.Column("status", sa.String(40), server_default="pending"),
        sa.Column("input_query", sa.Text(), nullable=True),
        sa.Column("draft_body", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("meta", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_ce_tasks_status", "ce_content_tasks", ["status"])

    op.create_table(
        "ce_distribution_channels",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("channel_type", sa.String(60), server_default="generic"),
        sa.Column("template_key", sa.String(120), nullable=True),
        sa.Column("webhook_url", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true()),
        sa.Column("meta", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("ce_distribution_channels")
    op.drop_table("ce_content_tasks")
    op.drop_table("ce_content_prompts")
    op.drop_table("ce_knowledge_chunks")
    op.drop_table("ce_knowledge_documents")
    op.drop_table("ce_knowledge_bases")
