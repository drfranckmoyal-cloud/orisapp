"""Dictionnaire, préférences et suggestions du praticien (spec §54, §120, §123, §176).

Trois règles tiennent tout :
- une personnalisation améliore la reconnaissance et le style, elle n'insère jamais un
  fait clinique ;
- rien ne devient permanent sans accord explicite : Oris **propose**, le praticien
  décide (§123) ;
- tout est réversible : un terme se désactive, une préférence revient au défaut (§177).
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from oris_api.db.models import GlossaryTermRow, LearningEventRow, User
from oris_api.domain.preferences import PractitionerPreferences, PreferencesPatch
from oris_api.domain.types import GlossaryHint
from oris_api.services.errors import Conflict, NotFound
from oris_api.services.identity import Actor

# Nombre de fois qu'une correction doit revenir avant qu'Oris n'en propose une règle.
SUGGESTION_THRESHOLD = 2
LENGTH_PREFERENCE = {
    "compte rendu plus court": ("document_length", "concise"),
    "compte rendu plus détaillé": ("document_length", "standard"),
}


@dataclass(frozen=True)
class Suggestion:
    """Une habitude constatée, proposée — jamais appliquée d'office."""

    key: str
    kind: str  # "preference" | "glossary"
    message: str
    occurrences: int
    payload: dict[str, str]


def preferences_of(session: Session, actor: Actor) -> PractitionerPreferences:
    user = session.get(User, actor.user_id)
    if user is None:
        raise NotFound("USER_NOT_FOUND", str(actor.user_id))
    return PractitionerPreferences.load(user.preferences)


def update_preferences(
    session: Session, actor: Actor, patch: PreferencesPatch
) -> PractitionerPreferences:
    user = session.get(User, actor.user_id)
    if user is None:
        raise NotFound("USER_NOT_FOUND", str(actor.user_id))
    updated = patch.applied_to(PractitionerPreferences.load(user.preferences))
    user.preferences = updated.model_dump()
    session.flush()
    return updated


def list_terms(
    session: Session, actor: Actor, include_disabled: bool = True
) -> list[GlossaryTermRow]:
    statement = select(GlossaryTermRow).where(GlossaryTermRow.user_id == actor.user_id)
    if not include_disabled:
        statement = statement.where(GlossaryTermRow.status == "active")
    return list(session.scalars(statement.order_by(GlossaryTermRow.canonical)))


def add_term(
    session: Session,
    actor: Actor,
    canonical: str,
    aliases: list[str],
    category: str = "other",
    origin: str = "manual",
) -> GlossaryTermRow:
    """Ajoute un terme, ou enrichit ses variantes s'il existe déjà."""
    existing = session.scalar(
        select(GlossaryTermRow).where(
            GlossaryTermRow.user_id == actor.user_id, GlossaryTermRow.canonical == canonical
        )
    )
    if existing is not None:
        known = {alias.lower() for alias in existing.aliases}
        existing.aliases = [*existing.aliases, *[a for a in aliases if a.lower() not in known]]
        existing.frequency += 1
        existing.status = "active"
        session.flush()
        return existing
    term = GlossaryTermRow(
        organization_id=actor.organization_id,
        user_id=actor.user_id,
        canonical=canonical,
        aliases=aliases,
        category=category,
        origin=origin,
    )
    session.add(term)
    session.flush()
    return term


def update_term(
    session: Session,
    actor: Actor,
    term_id: UUID,
    canonical: str | None = None,
    aliases: list[str] | None = None,
    status: str | None = None,
) -> GlossaryTermRow:
    term = session.get(GlossaryTermRow, term_id)
    if term is None or term.user_id != actor.user_id:
        raise NotFound("GLOSSARY_TERM_NOT_FOUND", str(term_id))
    if status is not None and status not in {"active", "disabled"}:
        raise Conflict("UNKNOWN_GLOSSARY_STATUS", str(term_id), [status])
    if canonical:
        term.canonical = canonical
    if aliases is not None:
        term.aliases = aliases
    if status is not None:
        term.status = status
    session.flush()
    return term


def hints_for(session: Session, user_id: UUID) -> list[GlossaryHint]:
    """Dictionnaire du praticien, dans la forme attendue par les fournisseurs.

    Un terme désactivé ne sort pas : c'est ce qui rend l'apprentissage réversible.
    """
    terms = session.scalars(
        select(GlossaryTermRow).where(
            GlossaryTermRow.user_id == user_id, GlossaryTermRow.status == "active"
        )
    )
    hints: list[GlossaryHint] = []
    for term in terms:
        hints.append(GlossaryHint(heard=term.canonical, canonical=term.canonical))
        hints += [GlossaryHint(heard=alias, canonical=term.canonical) for alias in term.aliases]
    return hints


def suggestions(session: Session, actor: Actor) -> list[Suggestion]:
    """Habitudes constatées dans les corrections : proposées, jamais appliquées (§123)."""
    events = list(
        session.scalars(
            select(LearningEventRow).where(
                LearningEventRow.user_id == actor.user_id,
                LearningEventRow.learning_status == "captured",
            )
        )
    )
    current = preferences_of(session, actor)
    known = {term.canonical for term in list_terms(session, actor)}
    found: list[Suggestion] = []

    styles = Counter(
        str((event.after or {}).get("preference", ""))
        for event in events
        if event.event_type == "style_preference_detected"
    )
    for preference, count in styles.items():
        target = LENGTH_PREFERENCE.get(preference)
        if not preference or count < SUGGESTION_THRESHOLD or target is None:
            continue
        field, value = target
        if getattr(current, field) == value:
            continue
        found.append(
            Suggestion(
                key=f"preference:{field}:{value}",
                kind="preference",
                message=(
                    f"Vous avez demandé « {preference} » {count} fois. L'appliquer par défaut ?"
                ),
                occurrences=count,
                payload={"field": field, "value": value},
            )
        )

    materials = Counter(
        str((event.after or {}).get("value", ""))
        for event in events
        if event.event_type == "material_name_correction"
    )
    for value, count in materials.items():
        if not value or count < SUGGESTION_THRESHOLD or value in known:
            continue
        heard = sorted(
            {
                str((event.before or {}).get("value", ""))
                for event in events
                if event.event_type == "material_name_correction"
                and str((event.after or {}).get("value", "")) == value
                and (event.before or {}).get("value")
            }
        )
        found.append(
            Suggestion(
                key=f"glossary:{value}",
                kind="glossary",
                message=(
                    f"Vous avez corrigé {count} fois vers « {value} ». "
                    "L'ajouter à votre dictionnaire ?"
                ),
                occurrences=count,
                payload={"canonical": value, "aliases": "|".join(heard)},
            )
        )

    return sorted(found, key=lambda item: (-item.occurrences, item.key))
