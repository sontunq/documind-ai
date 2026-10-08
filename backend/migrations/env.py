from alembic import context
from sqlalchemy import create_engine, pool
from sqlalchemy.engine import Connection

from app.core.config import Settings
from app.infrastructure.db.models import Base

config = context.config
# A connection can be supplied by tests without changing the production URL.
connection = config.attributes.get("connection")


def run(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=Base.metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    context.configure(url=Settings().database_url.get_secret_value(),
                      target_metadata=Base.metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
elif connection is not None:
    run(connection)
else:
    engine = create_engine(Settings().database_url.get_secret_value(), poolclass=pool.NullPool)
    with engine.connect() as connection:
        run(connection)
    engine.dispose()
