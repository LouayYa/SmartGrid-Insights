"""Convert the Date column from VARCHAR to a real, indexed DATE.

The dataset's mixed d/m/yy and d/m/yyyy strings meant date-range queries
had to load every row and filter in Python. Converting in place (with a
format-aware USING clause) lets range filters run as an indexed SQL
BETWEEN instead.

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-06

"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

TABLE = "household_power_consumption"


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        # Rows ending in a 4-digit year are d/m/yyyy; the rest are d/m/yy
        # (Postgres resolves 2-digit years to the nearest century, so
        # "07" -> 2007). FM suppresses zero-padding requirements.
        op.execute(
            f'''
            ALTER TABLE {TABLE}
            ALTER COLUMN "Date" TYPE DATE
            USING CASE
                WHEN "Date" ~ '/\\d{{4}}$' THEN to_date("Date", 'FMDD/FMMM/YYYY')
                ELSE to_date("Date", 'FMDD/FMMM/YY')
            END
            '''
        )
    else:
        # SQLite (dev fallback) can't ALTER COLUMN TYPE; batch mode rebuilds
        # the table. Data conversion is not attempted — dev data is reloaded
        # via POST /api/v1/load anyway.
        with op.batch_alter_table(TABLE) as batch:
            batch.alter_column("Date", type_=sa.Date(), nullable=False)

    op.create_index(op.f("ix_household_power_consumption_Date"), TABLE, ["Date"])


def downgrade() -> None:
    op.drop_index(op.f("ix_household_power_consumption_Date"), table_name=TABLE)
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            f'''
            ALTER TABLE {TABLE}
            ALTER COLUMN "Date" TYPE VARCHAR(20)
            USING to_char("Date", 'FMDD/FMMM/YYYY')
            '''
        )
    else:
        with op.batch_alter_table(TABLE) as batch:
            batch.alter_column("Date", type_=sa.String(length=20), nullable=False)
