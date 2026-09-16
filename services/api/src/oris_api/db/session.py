"""Moteur et sessions SQLAlchemy."""

from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from oris_api.config import get_settings


@lru_cache
def get_engine() -> Engine:
    # echo=False : les requêtes SQL et leurs paramètres ne vont jamais dans les logs.
    return create_engine(get_settings().database_url, pool_pre_ping=True, echo=False)


def get_session() -> Iterator[Session]:
    factory = sessionmaker(bind=get_engine(), expire_on_commit=False)
    with factory() as session:
        yield session
