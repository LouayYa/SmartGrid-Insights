"""Initial schema — the meters table.

Databases that predate Alembic already have this table from
db.create_all(), so the upgrade is a no-op when it exists — that adopts
the live schema without touching data.

Revision ID: 0001
Revises:
Create Date: 2026-07-06

"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

TABLE = "meters"


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table(TABLE):
        return

    op.create_table(
        TABLE,
        sa.Column("meter_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("meter_id"),
        sa.UniqueConstraint("name"),
    )


def downgrade() -> None:
    op.drop_table(TABLE)
