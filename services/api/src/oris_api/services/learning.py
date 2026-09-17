"""Émission des LearningEvents dans le store `learning` (spec §116–118, §127).

Contenu minimisé : identifiants de faits, concepts, valeurs corrigées ; jamais
l'identité du patient. Portée `user`, jamais éligible au global automatiquement.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from oris_api.contracts import validate_contract
from oris_api.contracts.generated import LearningEventEventType
from oris_api.db.models import LearningEventRow
from oris_api.domain.corrections import LearningEventDraft
from oris_api.services.identity import Actor


def emit(
    session: Session,
    actor: Actor,
    encounter_id: UUID,
    source_object_version: int,
    event_type: LearningEventEventType,
    before: Any,
    after: Any,
    confidence_before: float | None = None,
) -> LearningEventRow:
    row = LearningEventRow(
        organization_id=actor.organization_id,
        user_id=actor.user_id,
        encounter_id=encounter_id,
        event_type=event_type,
        scope="user",
        source_version=f"clinical_object_v{source_object_version}",
        before=before,
        after=after,
        reason=None,
        confidence_before=confidence_before,
        validated_by_practitioner=True,
        eligible_for_global_learning=False,
        learning_status="captured",
    )
    session.add(row)
    session.flush()
    validate_contract("LearningEvent", to_contract(row))
    return row


def emit_drafts(
    session: Session,
    actor: Actor,
    encounter_id: UUID,
    source_object_version: int,
    drafts: list[LearningEventDraft],
) -> None:
    for draft in drafts:
        emit(
            session,
            actor,
            encounter_id,
            source_object_version,
            draft.event_type,
            draft.before,
            draft.after,
            draft.confidence_before,
        )


def to_contract(row: LearningEventRow) -> dict[str, Any]:
    return {
        "learning_event_id": str(row.id),
        "organization_id": str(row.organization_id),
        "user_id": str(row.user_id),
        "encounter_id": str(row.encounter_id),
        "event_type": row.event_type,
        "scope": row.scope,
        "source_version": row.source_version,
        "before": row.before,
        "after": row.after,
        "reason": row.reason,
        "confidence_before": row.confidence_before,
        "validated_by_practitioner": row.validated_by_practitioner,
        "created_at": row.created_at.isoformat(),
        "eligible_for_global_learning": row.eligible_for_global_learning,
        "learning_status": row.learning_status,
    }


def list_for_encounter(
    session: Session, actor: Actor, encounter_id: UUID
) -> list[LearningEventRow]:
    return list(
        session.scalars(
            select(LearningEventRow)
            .where(
                LearningEventRow.encounter_id == encounter_id,
                LearningEventRow.organization_id == actor.organization_id,
            )
            .order_by(LearningEventRow.created_at)
        )
    )
