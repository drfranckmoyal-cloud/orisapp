"""Identité de démonstration tant que l'authentification n'existe pas (M10).

Uniquement en `local` et `test` : ailleurs, toute route métier est refusée.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from oris_api.config import Settings
from oris_api.db.models import Organization, OrganizationMember, User
from oris_api.services.errors import Forbidden

DEMO_EMAIL = "praticien.demo@oris.local"


@dataclass(frozen=True)
class Actor:
    organization_id: UUID
    user_id: UUID


def demo_actor(session: Session, settings: Settings) -> Actor:
    if settings.app_env not in {"local", "test"}:
        raise Forbidden("AUTHENTICATION_NOT_IMPLEMENTED")
    user = session.scalar(select(User).where(User.email == DEMO_EMAIL))
    if user is None:
        organization = Organization(name="Cabinet de démonstration")
        user = User(email=DEMO_EMAIL, name="Franck Moyal", role="practitioner")
        session.add_all([organization, user])
        session.flush()
        session.add(
            OrganizationMember(
                organization_id=organization.id, user_id=user.id, role="practitioner"
            )
        )
        session.commit()
        return Actor(organization.id, user.id)
    member = session.scalar(select(OrganizationMember).where(OrganizationMember.user_id == user.id))
    if member is None:
        raise Forbidden("NO_ORGANIZATION")
    return Actor(member.organization_id, user.id)
