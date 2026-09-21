"""Routes des photos d'un document (« Documentation clinique »)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from oris_api.api.dependencies import ActorDep, SessionDep
from oris_api.api.schemas import FigureOut, FiguresIn
from oris_api.db.models import Attachment, DocumentFigure
from oris_api.services import figures

router = APIRouter(tags=["documents"])


def _out(lignes: list[tuple[DocumentFigure, Attachment]]) -> list[FigureOut]:
    return [
        FigureOut(
            attachment_id=piece.id,
            caption=figure.caption,
            position=figure.position,
            filename=piece.filename,
            media_type=piece.media_type,
        )
        for figure, piece in lignes
    ]


@router.get("/documents/{document_id}/figures", response_model=list[FigureOut])
def list_figures(document_id: UUID, session: SessionDep, actor: ActorDep) -> list[FigureOut]:
    return _out(figures.lister(session, actor, document_id))


@router.put("/documents/{document_id}/figures", response_model=list[FigureOut])
def set_figures(
    document_id: UUID, body: FiguresIn, session: SessionDep, actor: ActorDep
) -> list[FigureOut]:
    """Pose la liste entière : ajouter, retirer, réordonner et légender en un geste."""
    choix = [(f.attachment_id, f.caption) for f in body.figures]
    return _out(figures.remplacer(session, actor, document_id, choix))
