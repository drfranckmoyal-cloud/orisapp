"""Envois de documents : noter à qui un compte rendu est parti.

Oris n'envoie rien lui-même. Le praticien envoie par mail, par courrier, ou remet le
document en main propre, puis le note ici : la liste des consultations dit alors
« envoyé au Dr Martin » au lieu de laisser chercher dans sa messagerie.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from oris_api.db.models import DocumentDelivery, DocumentRow, Encounter
from oris_api.services import audit, correspondents
from oris_api.services.errors import NotFound, Unprocessable
from oris_api.services.identity import Actor

CANAUX: frozenset[str] = frozenset({"email", "mail", "hand", "secure_messaging", "other"})
DESTINATAIRES: frozenset[str] = frozenset({"patient", "correspondent", "other"})


def _document(session: Session, actor: Actor, document_id: UUID) -> DocumentRow:
    document = session.get(DocumentRow, document_id)
    encounter = session.get(Encounter, document.encounter_id) if document else None
    if document is None or encounter is None or encounter.organization_id != actor.organization_id:
        raise NotFound("DOCUMENT_NOT_FOUND", str(document_id))
    return document


def noter(
    session: Session,
    actor: Actor,
    document_id: UUID,
    recipient_kind: str,
    channel: str,
    correspondent_id: UUID | None = None,
    recipient_label: str = "",
) -> DocumentDelivery:
    """Note un envoi. Le nom affiché est recopié maintenant, pas relu plus tard."""
    _document(session, actor, document_id)
    if channel not in CANAUX:
        raise Unprocessable("DELIVERY_CHANNEL_UNKNOWN", details=[channel])
    if recipient_kind not in DESTINATAIRES:
        raise Unprocessable("DELIVERY_RECIPIENT_UNKNOWN", details=[recipient_kind])

    libelle = recipient_label.strip()
    if recipient_kind == "patient":
        libelle = "le patient"
        correspondent_id = None
    elif recipient_kind == "correspondent":
        if correspondent_id is None:
            raise Unprocessable("DELIVERY_RECIPIENT_MISSING")
        fiche = correspondents.get_correspondent(session, actor, correspondent_id)
        libelle = " ".join(part for part in (fiche.title, fiche.last_name) if part)
    else:
        correspondent_id = None
        if not libelle:
            raise Unprocessable("DELIVERY_RECIPIENT_MISSING")

    envoi = DocumentDelivery(
        organization_id=actor.organization_id,
        document_id=document_id,
        recipient_kind=recipient_kind,
        correspondent_id=correspondent_id,
        recipient_label=libelle[:200],
        channel=channel,
        created_by=actor.user_id,
    )
    session.add(envoi)
    session.flush()
    # Jamais le nom du destinataire dans le journal : des identifiants, rien d'autre.
    audit.record(
        session, actor, "document.delivery_noted", "document", document_id, channel=channel
    )
    return envoi


def envois_de(session: Session, encounter_id: UUID) -> list[DocumentDelivery]:
    """Les envois des documents d'une consultation, du plus ancien au plus récent."""
    return list(
        session.scalars(
            select(DocumentDelivery)
            .join(DocumentRow, DocumentRow.id == DocumentDelivery.document_id)
            .where(DocumentRow.encounter_id == encounter_id)
            .order_by(DocumentDelivery.sent_at)
        )
    )


def annuler(session: Session, actor: Actor, delivery_id: UUID) -> None:
    """Retirer un envoi noté par erreur."""
    envoi = session.get(DocumentDelivery, delivery_id)
    if envoi is None or envoi.organization_id != actor.organization_id:
        raise NotFound("DELIVERY_NOT_FOUND", str(delivery_id))
    session.delete(envoi)
    audit.record(session, actor, "document.delivery_removed", "document", envoi.document_id)
