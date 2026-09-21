"""Routes du carnet d'adresses (correspondants).

Un correspondant n'est pas un utilisateur : c'est une fiche d'adresse, qui sert à
rattacher un patient et à écrire le courrier d'adressage.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, status

from oris_api.api.dependencies import ActorDep, SessionDep
from oris_api.api.schemas import (
    CorrespondentCreate,
    CorrespondentOut,
    CorrespondentUpdate,
    SpecialtyIn,
)
from oris_api.services import correspondents

router = APIRouter(prefix="/correspondents", tags=["correspondents"])


@router.get("/specialties", response_model=list[str])
def list_specialties(session: SessionDep, actor: ActorDep) -> list[str]:
    """Celles connues d'avance, puis celles que le cabinet a ajoutées."""
    return correspondents.specialites(session, actor)


@router.post("/specialties", response_model=list[str], status_code=status.HTTP_201_CREATED)
def add_specialty(body: SpecialtyIn, session: SessionDep, actor: ActorDep) -> list[str]:
    correspondents.ajouter_specialite(session, actor, body.label)
    return correspondents.specialites(session, actor)


@router.delete("/specialties/{label}", response_model=list[str])
def remove_specialty(label: str, session: SessionDep, actor: ActorDep) -> list[str]:
    correspondents.retirer_specialite(session, actor, label)
    return correspondents.specialites(session, actor)


@router.get("", response_model=list[CorrespondentOut])
def list_correspondents(
    session: SessionDep, actor: ActorDep, q: str | None = None, specialty: str | None = None
) -> list[CorrespondentOut]:
    return [
        CorrespondentOut.model_validate(c)
        for c in correspondents.list_correspondents(session, actor, q, specialty)
    ]


@router.post("", response_model=CorrespondentOut, status_code=status.HTTP_201_CREATED)
def create_correspondent(
    body: CorrespondentCreate, session: SessionDep, actor: ActorDep
) -> CorrespondentOut:
    return CorrespondentOut.model_validate(
        correspondents.create_correspondent(session, actor, **body.model_dump())
    )


@router.get("/{correspondent_id}", response_model=CorrespondentOut)
def get_correspondent(
    correspondent_id: UUID, session: SessionDep, actor: ActorDep
) -> CorrespondentOut:
    return CorrespondentOut.model_validate(
        correspondents.get_correspondent(session, actor, correspondent_id)
    )


@router.patch("/{correspondent_id}", response_model=CorrespondentOut)
def update_correspondent(
    correspondent_id: UUID, body: CorrespondentUpdate, session: SessionDep, actor: ActorDep
) -> CorrespondentOut:
    changes = body.model_dump(exclude_unset=True)
    return CorrespondentOut.model_validate(
        correspondents.update_correspondent(session, actor, correspondent_id, changes)
    )


@router.delete("/{correspondent_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_correspondent(correspondent_id: UUID, session: SessionDep, actor: ActorDep) -> None:
    correspondents.delete_correspondent(session, actor, correspondent_id)
