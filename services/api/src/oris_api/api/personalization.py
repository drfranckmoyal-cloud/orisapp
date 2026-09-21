"""Routes de personnalisation : dictionnaire, préférences, suggestions (spec §54, §124).

Oris propose, le praticien décide, et tout se défait : un terme se désactive, une
préférence revient au défaut (§177).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from oris_api.api.dependencies import ActorDep, SessionDep
from oris_api.contracts.generated import PractitionerLearningProfile
from oris_api.db.models import GlossaryTermRow, ModelVersion, Organization, PromptVersion, User
from oris_api.domain.preferences import PractitionerPreferences, PreferencesPatch
from oris_api.services import personalization
from oris_api.services.errors import NotFound

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


class FrequentCorrectionOut(BaseModel):
    event_type: str
    detail: str
    occurrences: int


class PreferenceReset(BaseModel):
    """Champ à remettre au défaut ; absent, tout revient au défaut."""

    model_config = ConfigDict(extra="forbid")
    field: Annotated[str, Field(max_length=60)] | None = None


class LearningExport(BaseModel):
    """Tout ce qu'Oris a retenu de vous, en un fichier lisible (§124)."""

    exported_at: datetime
    practitioner: str
    preferences: PractitionerPreferences
    glossary: list[GlossaryTermOut]


class EngineVersionOut(BaseModel):
    """Un moteur qui a réellement servi, et la consigne qui l'accompagnait."""

    component: str
    provider: str
    model_id: str
    prompt_version: str | None
    first_seen_at: datetime


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


class CabinetOut(BaseModel):
    """Identité imprimée en tête des documents (spec §78)."""

    name: str
    address: str = ""
    phone: str = ""
    email: str = ""
    legal: str = ""
    city: str = ""
    practitioner_title: str = ""
    #: Une ligne par titre, imprimées sous le nom (« Chirurgien-dentiste »…).
    qualifications: str = ""
    practitioner_name: str = ""


class CabinetPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Annotated[str, Field(max_length=200)] | None = None
    address: Annotated[str, Field(max_length=300)] | None = None
    phone: Annotated[str, Field(max_length=60)] | None = None
    email: Annotated[str, Field(max_length=200)] | None = None
    legal: Annotated[str, Field(max_length=200)] | None = None
    city: Annotated[str, Field(max_length=120)] | None = None
    practitioner_title: Annotated[str, Field(max_length=80)] | None = None
    qualifications: Annotated[str, Field(max_length=400)] | None = None


def cabinet_out(organisation: Organization, praticien: User | None) -> CabinetOut:
    identite = dict(organisation.identity or {})
    return CabinetOut(
        name=identite.get("name") or organisation.name,
        address=identite.get("address", ""),
        phone=identite.get("phone", ""),
        email=identite.get("email", ""),
        legal=identite.get("legal", ""),
        city=identite.get("city", ""),
        practitioner_title=identite.get("practitioner_title", ""),
        qualifications=identite.get("qualifications", ""),
        practitioner_name=praticien.name if praticien else "",
    )


@router.get("/me/cabinet", response_model=CabinetOut)
def read_cabinet(session: SessionDep, actor: ActorDep) -> CabinetOut:
    organisation = session.get(Organization, actor.organization_id)
    if organisation is None:
        raise NotFound("ORGANIZATION_NOT_FOUND", str(actor.organization_id))
    return cabinet_out(organisation, session.get(User, actor.user_id))


@router.patch("/me/cabinet", response_model=CabinetOut)
def patch_cabinet(body: CabinetPatch, session: SessionDep, actor: ActorDep) -> CabinetOut:
    """Ce que le praticien saisit ici s'imprime en tête de ses documents."""
    organisation = session.get(Organization, actor.organization_id)
    if organisation is None:
        raise NotFound("ORGANIZATION_NOT_FOUND", str(actor.organization_id))
    identite = dict(organisation.identity or {})
    identite.update(body.model_dump(exclude_none=True))
    organisation.identity = identite
    if body.name:
        organisation.name = body.name
    session.flush()
    return cabinet_out(organisation, session.get(User, actor.user_id))


@router.get("/ontology/concepts", response_model=dict[str, str])
def read_concepts() -> dict[str, str]:
    """Vocabulaire d'Oris : code technique -> mot français.

    L'interface ne doit jamais montrer `cold_sensitivity` à un praticien.
    """
    from oris_api.ontology.labels import CONCEPTS

    return {concept: label.label for concept, label in sorted(CONCEPTS.items())}


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


@router.post("/me/preferences/reset", response_model=PractitionerPreferences)
def reset_preferences(
    body: PreferenceReset, session: SessionDep, actor: ActorDep
) -> PractitionerPreferences:
    """Revenir au défaut d'Oris. Le dictionnaire n'est pas touché (§124, §177)."""
    return personalization.reset_preferences(session, actor, body.field)


@router.get("/me/learning/corrections", response_model=list[FrequentCorrectionOut])
def list_frequent_corrections(session: SessionDep, actor: ActorDep) -> list[FrequentCorrectionOut]:
    """Ce que vous corrigez le plus souvent. Oris le montre, il n'en déduit rien."""
    return [
        FrequentCorrectionOut(
            event_type=item.event_type, detail=item.detail, occurrences=item.occurrences
        )
        for item in personalization.frequent_corrections(session, actor)
    ]


@router.get("/me/learning/export", response_model=LearningExport)
def export_learning(session: SessionDep, actor: ActorDep) -> LearningExport:
    """Emporter ses préférences et son dictionnaire : rien n'est enfermé dans Oris."""
    praticien = session.get(User, actor.user_id)
    return LearningExport(
        exported_at=datetime.now(UTC),
        practitioner=praticien.name if praticien else "",
        preferences=personalization.preferences_of(session, actor),
        glossary=[term_out(term) for term in personalization.list_terms(session, actor)],
    )


@router.get("/me/learning/profile", response_model=PractitionerLearningProfile)
def read_learning_profile(session: SessionDep, actor: ActorDep) -> PractitionerLearningProfile:
    """Ce qu'Oris croit savoir de vous, d'un bloc (§202, §205).

    C'est un miroir : il se recalcule à partir des préférences et du dictionnaire, et
    ne contient rien de clinique.
    """
    row = personalization.refresh_profile(session, actor)
    return PractitionerLearningProfile.model_validate(row.profile)


@router.get("/system/versions", response_model=list[EngineVersionOut])
def list_engine_versions(session: SessionDep) -> list[EngineVersionOut]:
    """Quel moteur et quelle consigne ont réellement servi (§202).

    Ces lignes sont écrites par le traitement lui-même : elles disent ce qui a tourné,
    pas ce qui est configuré.
    """
    modeles = session.scalars(
        select(ModelVersion).where(ModelVersion.is_active).order_by(ModelVersion.component)
    )
    invites = {
        row.component: row
        for row in session.scalars(select(PromptVersion).where(PromptVersion.is_active))
    }
    return [
        EngineVersionOut(
            component=modele.component,
            provider=modele.provider,
            model_id=modele.model_id,
            prompt_version=(
                invites[modele.component].version if modele.component in invites else None
            ),
            first_seen_at=modele.created_at,
        )
        for modele in modeles
    ]


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
