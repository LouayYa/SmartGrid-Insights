"""Initial schema — household_power_consumption as originally deployed.

Captures the historical schema (Date stored as VARCHAR, verbatim from the
CSV). Databases that predate Alembic already have this table from
Base.metadata.create_all(), so the upgrade is a no-op when it exists —
that adopts the live schema without touching data.

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

TABLE = "household_power_consumption"


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table(TABLE):
        return

    op.create_table(
        TABLE,
        sa.Column("ID", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("Date", sa.String(length=20), nullable=False),
        sa.Column("Time", sa.String(length=20), nullable=False),
        sa.Column("Global_active_power", sa.Float(), nullable=True),
        sa.Column("Global_reactive_power", sa.Float(), nullable=True),
        sa.Column("Voltage", sa.Float(), nullable=True),
        sa.Column("Global_intensity", sa.Float(), nullable=True),
        sa.Column("Sub_metering_1", sa.Float(), nullable=True),
        sa.Column("Sub_metering_2", sa.Float(), nullable=True),
        sa.Column("Sub_metering_3", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint("ID"),
    )
    op.create_index(op.f("ix_household_power_consumption_ID"), TABLE, ["ID"])


def downgrade() -> None:
    op.drop_index(op.f("ix_household_power_consumption_ID"), table_name=TABLE)
    op.drop_table(TABLE)
