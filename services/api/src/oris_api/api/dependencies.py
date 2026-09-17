"""Dépendances communes des routes."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from oris_api.config import Settings, get_settings
from oris_api.db.session import get_session
from oris_api.providers import ProviderSet
from oris_api.services.identity import Actor, demo_actor


def transactional_session(session: Annotated[Session, Depends(get_session)]) -> Iterator[Session]:
    """Une requête = une transaction : validée si la route réussit, annulée sinon."""
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise


SessionDep = Annotated[Session, Depends(transactional_session)]


def current_actor(
    session: SessionDep, settings: Annotated[Settings, Depends(get_settings)]
) -> Actor:
    return demo_actor(session, settings)


def providers(request: Request) -> ProviderSet:
    provider_set: ProviderSet = request.app.state.providers
    return provider_set


ActorDep = Annotated[Actor, Depends(current_actor)]
ProvidersDep = Annotated[ProviderSet, Depends(providers)]
