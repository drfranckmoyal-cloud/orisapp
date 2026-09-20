"""Routes de personnalisation : dictionnaire, préférences, suggestions (spec §54, §124).

Oris propose, le praticien décide, et tout se défait : un terme se désactive, une
préférence revient au défaut (§177).
"""

from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from oris_api.api.dependencies import ActorDep, SessionDep
from oris_api.db.models import GlossaryTermRow
from oris_api.domain.preferences import PractitionerPreferences, PreferencesPatch
from oris_api.services import personalization

router = APIRouter(tags=["personnalisation"])


class GlossaryTermOut(BaseModel):
    id: UUID
    canonical: str
    aliases: list[str]
    category: str
    origin: str
    status: str
    frequency: int


class NewGlossaryTerm(BaseModel):
    model_config = ConfigDict(extra="forbid")
    canonical: Annotated[str, Field(min_length=1, max_length=200)]
    aliases: Annotated[list[str], Field(max_length=20)] = []
    category: Annotated[str, Field(max_length=40)] = "other"


class GlossaryTermPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    canonical: Annotated[str, Field(min_length=1, max_length=200)] | None = None
    aliases: Annotated[list[str], Field(max_length=20)] | None = None
    status: Literal["active", "disabled"] | None = None


class SuggestionOut(BaseModel):
    key: str
    kind: str
    message: str
    occurrences: int
    payload: dict[str, str]


def term_out(term: GlossaryTermRow) -> GlossaryTermOut:
    return GlossaryTermOut(
        id=term.id,
        canonical=term.canonical,
        aliases=list(term.aliases),
        category=term.category,
        origin=term.origin,
        status=term.status,
        frequency=term.frequency,
    )


@router.get("/me/preferences", response_model=PractitionerPreferences)
def read_preferences(session: SessionDep, actor: ActorDep) -> PractitionerPreferences:
    return personalization.preferences_of(session, actor)


@router.patch("/me/preferences", response_model=PractitionerPreferences)
def patch_preferences(
    body: PreferencesPatch, session: SessionDep, actor: ActorDep
) -> PractitionerPreferences:
    """Ne change que la forme des documents ; le dossier clinique n'est pas touché."""
    return personalization.update_preferences(session, actor, body)


@router.get("/glossary", response_model=list[GlossaryTermOut])
def list_glossary(session: SessionDep, actor: ActorDep) -> list[GlossaryTermOut]:
    return [term_out(term) for term in personalization.list_terms(session, actor)]


@router.post("/glossary", response_model=GlossaryTermOut, status_code=201)
def add_glossary_term(
    body: NewGlossaryTerm, session: SessionDep, actor: ActorDep
) -> GlossaryTermOut:
    term = personalization.add_term(
        session, actor, body.canonical, list(body.aliases), body.category
    )
    return term_out(term)


@router.patch("/glossary/{term_id}", response_model=GlossaryTermOut)
def patch_glossary_term(
    term_id: UUID, body: GlossaryTermPatch, session: SessionDep, actor: ActorDep
) -> GlossaryTermOut:
    """Corriger un terme, ou le désactiver : l'apprentissage doit être réversible."""
    term = personalization.update_term(
        session,
        actor,
        term_id,
        canonical=body.canonical,
        aliases=list(body.aliases) if body.aliases is not None else None,
        status=body.status,
    )
    return term_out(term)


@router.get("/me/learning/suggestions", response_model=list[SuggestionOut])
def list_suggestions(session: SessionDep, actor: ActorDep) -> list[SuggestionOut]:
    """Habitudes constatées, proposées au praticien. Rien n'est appliqué d'office."""
    return [
        SuggestionOut(
            key=item.key,
            kind=item.kind,
            message=item.message,
            occurrences=item.occurrences,
            payload=item.payload,
        )
        for item in personalization.suggestions(session, actor)
    ]
