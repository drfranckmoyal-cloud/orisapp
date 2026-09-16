"""Environnement Alembic : cible la base de DATABASE_URL, tous schémas inclus."""

from __future__ import annotations

from logging.config import fileConfig

from sqlalchemy import create_engine

from alembic import context
from oris_api.config import get_settings
from oris_api.db import models  # noqa: F401  (enregistre les tables)
from oris_api.db.base import Base

config = context.config
if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def database_url() -> str:
    url = config.attributes.get("database_url")
    return url if isinstance(url, str) else get_settings().database_url


def run_migrations_offline() -> None:
    context.configure(
        url=database_url(),
        target_metadata=target_metadata,
        include_schemas=True,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(database_url())
    with engine.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata, include_schemas=True
        )
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
