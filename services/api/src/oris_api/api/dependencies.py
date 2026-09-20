"""Dépendances communes des routes."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from oris_api.config import Settings, get_settings
from oris_api.db.session import get_session
from oris_api.providers import ProviderSet
from oris_api.services import authentication
from oris_api.services.audio_sink import AudioSink
from oris_api.services.errors import Forbidden
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
    request: Request,
    session: SessionDep,
    settings: Annotated[Settings, Depends(get_settings)],
) -> Actor:
    """Praticien de la requête.

    En développement (`local`, `test`), l'identité de démonstration suffit tant qu'aucun
    jeton n'est présenté. Partout ailleurs, un jeton valide est exigé : il n'y a pas de
    mode « ouvert » en production (docs/SECURITY.md).
    """
    header = request.headers.get("authorization", "")
    presented = header[7:].strip() if header.lower().startswith("bearer ") else ""
    if presented:
        return authentication.actor_for(session, presented)
    if settings.app_env in {"local", "test"}:
        return demo_actor(session, settings)
    raise Forbidden("AUTHENTICATION_REQUIRED")


def providers(request: Request) -> ProviderSet:
    provider_set: ProviderSet = request.app.state.providers
    return provider_set


def audio_sink(request: Request) -> AudioSink:
    sink: AudioSink = request.app.state.audio_sink
    return sink


ActorDep = Annotated[Actor, Depends(current_actor)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
SinkDep = Annotated[AudioSink, Depends(audio_sink)]
ProvidersDep = Annotated[ProviderSet, Depends(providers)]
