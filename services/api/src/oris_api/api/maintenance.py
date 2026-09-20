"""Entretien et traçabilité : purge du son, lecture du journal (docs/SECURITY.md).

Le journal ne contient que des identifiants et des actions — jamais une phrase du
patient, un diagnostic ni un document. C'est vérifié par un test.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import select

from oris_api.api.dependencies import ActorDep, SessionDep, SinkDep
from oris_api.db.models import AuditEvent
from oris_api.services import audio as audio_service

router = APIRouter(tags=["entretien"])


class AuditEventOut(BaseModel):
    id: UUID
    action: str
    entity_type: str
    entity_id: UUID
    actor_user_id: UUID | None
    details: dict[str, Any]
    occurred_at: datetime


class PurgeReportOut(BaseModel):
    purged: list[UUID]
    failed: list[UUID]
    remaining: int


@router.get("/audit", response_model=list[AuditEventOut])
def read_audit(
    session: SessionDep,
    actor: ActorDep,
    encounter_id: UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[AuditEventOut]:
    """Qui a fait quoi, quand. Réservé aux consultations de l'organisation du praticien."""
    statement = (
        select(AuditEvent)
        .where(AuditEvent.organization_id == actor.organization_id)
        .order_by(AuditEvent.occurred_at.desc())
        .limit(limit)
    )
    if encounter_id is not None:
        statement = statement.where(AuditEvent.entity_id == encounter_id)
    rows = session.scalars(statement).unique()
    return [
        AuditEventOut(
            id=row.id,
            action=row.action,
            entity_type=row.entity_type,
            entity_id=row.entity_id,
            actor_user_id=row.actor_user_id,
            details=dict(row.details or {}),
            occurred_at=row.occurred_at,
        )
        for row in rows
    ]


@router.post("/maintenance/audio-purge", response_model=PurgeReportOut)
def run_audio_purge(session: SessionDep, actor: ActorDep, sink: SinkDep) -> PurgeReportOut:
    """Repasse la purge du son sur les consultations déjà traitées. Rejouable sans risque."""
    report = audio_service.purge_pending(session, sink)
    return PurgeReportOut(purged=report.purged, failed=report.failed, remaining=report.remaining)
