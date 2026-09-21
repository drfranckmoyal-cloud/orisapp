"""Photos d'un document : la page « Documentation clinique » des modèles du praticien.

Le praticien choisit des photos parmi les pièces jointes du patient et les légende.
Oris ne regarde pas les photos : il les place, dans l'ordre choisi.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from oris_api.db.models import Attachment, DocumentFigure, DocumentRow, Encounter
from oris_api.services import audit
from oris_api.services.attachments import Magasin, read_attachment
from oris_api.services.errors import NotFound, Unprocessable
from oris_api.services.identity import Actor
from oris_api.services.images import IMPRIMABLES, affichable

MAX_FIGURES = 12


@dataclass(frozen=True)
class Figure:
    """Une photo prête à imprimer."""

    contenu: bytes
    legende: str


def _document(session: Session, actor: Actor, document_id: UUID) -> tuple[DocumentRow, Encounter]:
    document = session.get(DocumentRow, document_id)
    encounter = session.get(Encounter, document.encounter_id) if document else None
    if document is None or encounter is None or encounter.organization_id != actor.organization_id:
        raise NotFound("DOCUMENT_NOT_FOUND", str(document_id))
    return document, encounter


def figures_de(session: Session, document_id: UUID) -> list[tuple[DocumentFigure, Attachment]]:
    lignes = session.execute(
        select(DocumentFigure, Attachment)
        .join(Attachment, Attachment.id == DocumentFigure.attachment_id)
        .where(DocumentFigure.document_id == document_id)
        .order_by(DocumentFigure.position)
    )
    return [(figure, piece) for figure, piece in lignes]


def lister(
    session: Session, actor: Actor, document_id: UUID
) -> list[tuple[DocumentFigure, Attachment]]:
    _document(session, actor, document_id)
    return figures_de(session, document_id)


def remplacer(
    session: Session, actor: Actor, document_id: UUID, choix: list[tuple[UUID, str]]
) -> list[tuple[DocumentFigure, Attachment]]:
    """Pose la liste entière, dans l'ordre donné : ajouter, retirer, réordonner, légender."""
    document, encounter = _document(session, actor, document_id)
    if len(choix) > MAX_FIGURES:
        raise Unprocessable("TOO_MANY_FIGURES", str(document_id), [str(MAX_FIGURES)])
    vus: set[UUID] = set()
    for attachment_id, _ in choix:
        piece = session.get(Attachment, attachment_id)
        if piece is None or piece.patient_id != encounter.patient_id:
            raise NotFound("ATTACHMENT_NOT_FOUND", str(attachment_id))
        if piece.media_type not in IMPRIMABLES:
            raise Unprocessable("FIGURE_NOT_PRINTABLE", str(attachment_id), [piece.media_type])
        if attachment_id in vus:
            raise Unprocessable("FIGURE_DUPLICATED", str(attachment_id))
        vus.add(attachment_id)

    session.execute(delete(DocumentFigure).where(DocumentFigure.document_id == document.id))
    for position, (attachment_id, legende) in enumerate(choix):
        session.add(
            DocumentFigure(
                document_id=document.id,
                attachment_id=attachment_id,
                caption=legende.strip()[:300],
                position=position,
            )
        )
    session.flush()
    audit.record(session, actor, "document.figures_set", "document", document.id, count=len(choix))
    return figures_de(session, document.id)


def a_imprimer(session: Session, magasin: Magasin, document_id: UUID) -> tuple[Figure, ...]:
    """Les photos du document, lues du magasin. Une photo disparue du disque est sautée
    plutôt que de faire échouer tout le document : sa pièce jointe le signale déjà."""
    imprimees: list[Figure] = []
    for figure, piece in figures_de(session, document_id):
        try:
            contenu, _ = affichable(read_attachment(magasin, piece), piece.media_type)
            imprimees.append(Figure(contenu, figure.caption))
        except NotFound:
            continue
    return tuple(imprimees)
