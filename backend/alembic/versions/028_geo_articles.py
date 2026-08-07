"""geo_articles table for article management

Revision ID: 028_geo_articles
Revises: 027_real_obs_diagnosis_type
Create Date: 2026-08-07
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "028_geo_articles"
down_revision = "027_real_obs_diagnosis_type"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "geo_articles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("source_type", sa.String(length=40), nullable=False, server_default="local"),
        sa.Column("lifecycle_status", sa.String(length=40), nullable=False, server_default="draft"),
        sa.Column("origin", sa.String(length=40), nullable=False, server_default="user"),
        sa.Column("published_url", sa.String(length=800), nullable=True),
        sa.Column("channel", sa.String(length=80), nullable=True),
        sa.Column("strategy_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("knowledge_base_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("content_task_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("citation_count_30d", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_geo_articles_source_type", "geo_articles", ["source_type"])
    op.create_index("ix_geo_articles_lifecycle_status", "geo_articles", ["lifecycle_status"])
    op.create_index("ix_geo_articles_origin", "geo_articles", ["origin"])
    op.create_index("ix_geo_articles_strategy_id", "geo_articles", ["strategy_id"])
    op.create_index("ix_geo_articles_knowledge_base_id", "geo_articles", ["knowledge_base_id"])
    op.create_index("ix_geo_articles_content_task_id", "geo_articles", ["content_task_id"])
    op.create_index("ix_geo_articles_owner_user_id", "geo_articles", ["owner_user_id"])
    op.create_index("ix_geo_articles_created_at", "geo_articles", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_geo_articles_created_at", table_name="geo_articles")
    op.drop_index("ix_geo_articles_owner_user_id", table_name="geo_articles")
    op.drop_index("ix_geo_articles_content_task_id", table_name="geo_articles")
    op.drop_index("ix_geo_articles_knowledge_base_id", table_name="geo_articles")
    op.drop_index("ix_geo_articles_strategy_id", table_name="geo_articles")
    op.drop_index("ix_geo_articles_origin", table_name="geo_articles")
    op.drop_index("ix_geo_articles_lifecycle_status", table_name="geo_articles")
    op.drop_index("ix_geo_articles_source_type", table_name="geo_articles")
    op.drop_table("geo_articles")
