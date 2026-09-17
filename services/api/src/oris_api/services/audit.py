"""Journal d'audit clinique : actions et identifiants, jamais de contenu (spec §89)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from oris_api.db.models import AuditEvent
from oris_api.services.identity import Actor


def record(
    session: Session,
    actor: Actor | None,
    action: str,
    entity_type: str,
    entity_id: UUID,
    **details: Any,
) -> None:
    session.add(
        AuditEvent(
            organization_id=actor.organization_id if actor else None,
            actor_user_id=actor.user_id if actor else None,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
        )
    )
