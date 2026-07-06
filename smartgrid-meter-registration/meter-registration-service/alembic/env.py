import os
import sys

from dotenv import load_dotenv
from sqlalchemy import create_engine, pool

from alembic import context

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

# Import the Flask-SQLAlchemy models; db.metadata carries the schema without
# needing an app context.
from models import db  # noqa: E402

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./meters.db")

config = context.config
target_metadata = db.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(DATABASE_URL, poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
