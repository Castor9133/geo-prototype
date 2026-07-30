"""Apply a reviewed public expert state transition."""

from datetime import date
import json
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = '020_unpublish_yao_jingang'
down_revision = '019_add_geo_runs'
branch_labels = None
depends_on = None

EFFECTIVE_DATE = date.fromisoformat('2026-07-30')
DOWNGRADE_POLICY = 'preserve_target_state'
STATE_TRANSITIONS = json.loads('[{"operation":"set_publication_state","id":"2dfd3c38-5c50-4e89-8a64-6be1db151e74","slug":"yao-jingang","from_state":{"is_published":true,"is_featured":true},"to_state":{"is_published":false,"is_featured":false},"reason":"maintainer fork cleanup: remove upstream author profile from public channel"}]')
for _transition in STATE_TRANSITIONS:
    _transition["id"] = uuid.UUID(_transition["id"])


def _expert_profiles_table():
    return sa.table(
        "expert_profiles",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("slug", sa.String(length=120)),
        sa.column("is_published", sa.Boolean()),
        sa.column("is_featured", sa.Boolean()),
    )


def _apply(connection, transition, accepted_states, target_state):
    table = _expert_profiles_table()
    accepted_state_clause = sa.or_(*[
        sa.and_(
            table.c.is_published.is_(state["is_published"]),
            table.c.is_featured.is_(state["is_featured"]),
        )
        for state in accepted_states
    ])
    statement = (
        table.update()
        .where(table.c.id == transition["id"])
        .where(table.c.slug == transition["slug"])
        .where(accepted_state_clause)
        .values(
            is_published=target_state["is_published"],
            is_featured=target_state["is_featured"],
        )
    )
    result = connection.execute(statement)
    if result.rowcount != 1:
        raise RuntimeError("expert state transition must match exactly one id/slug/state row")


def upgrade():
    connection = op.get_bind()
    for transition in STATE_TRANSITIONS:
        _apply(
            connection,
            transition,
            [transition["from_state"], transition["to_state"]],
            transition["to_state"],
        )


def downgrade():
    connection = op.get_bind()
    for transition in STATE_TRANSITIONS:
        _apply(connection, transition, [transition["to_state"]], transition["to_state"])
