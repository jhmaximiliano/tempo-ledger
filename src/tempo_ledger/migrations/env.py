"""Entorno de Alembic: aplica las migraciones sobre la URL configurada."""

from alembic import context
from sqlalchemy import engine_from_config, pool

from tempo_ledger.infra.db import database_url
from tempo_ledger.infra.models import Base

config = context.config
if not config.get_main_option("sqlalchemy.url"):
    config.set_main_option("sqlalchemy.url", database_url())

target_metadata = Base.metadata


def run_migrations_online() -> None:
    engine = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with engine.connect() as connection:
        # render_as_batch: SQLite no soporta ALTER TABLE completo; Alembic lo emula.
        context.configure(connection=connection, target_metadata=target_metadata,
                          render_as_batch=True)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


run_migrations_online()
