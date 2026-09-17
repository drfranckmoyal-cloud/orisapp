"""Application d'une correction clinique (spec §47, D016).

Ordre imposé : objet clinique d'abord, puis invalidation, puis régénération.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from oris_api.db.models import Encounter
from oris_api.domain.corrections import CorrectionError, CorrectionOperation, apply_operations
from oris_api.domain.resolver import resolve
from oris_api.providers import ProviderSet
from oris_api.services import audit, documents, learning
from oris_api.services.clinical_store import load_current, load_segments, save_version
from oris_api.services.encounters import transition
from oris_api.services.errors import Conflict, Unprocessable
from oris_api.services.identity import Actor

CORRECTABLE = frozenset({"review", "validated", "exported"})


def apply_correction(
    session: Session,
    actor: Actor,
    encounter: Encounter,
    expected_object_version: int,
    operations: list[CorrectionOperation],
    providers: ProviderSet,
    regenerate: bool = True,
) -> Encounter:
    if encounter.status not in CORRECTABLE:
        raise Conflict("ENCOUNTER_NOT_CORRECTABLE", str(encounter.id), [encounter.status])
    current = load_current(session, encounter)
    if expected_object_version != current.object_version:
        raise Conflict("OBJECT_VERSION_CONFLICT", str(encounter.id), [str(current.object_version)])

    try:
        result = apply_operations(current, operations)
    except CorrectionError as error:
        raise Unprocessable(error.code, error.subject_id) from error

    corrected = result.encounter
    violations = resolve(
        corrected.facts,
        corrected.treatment_plan,
        corrected.procedures,
        load_segments(session, encounter.id),
    )
    if violations:
        raise Unprocessable(
            "CORRECTION_REJECTED", str(encounter.id), sorted({v.rule for v in violations})
        )

    # 1. objet clinique
    save_version(session, encounter, corrected, "correction", created_by=actor.user_id)
    # 2. documents dérivés invalidés
    documents.mark_outdated(session, encounter.id)
    if encounter.status != "review":
        transition(session, actor, encounter, "review")
    # 3. apprentissage
    learning.emit_drafts(
        session, actor, encounter.id, current.object_version, result.learning_events
    )
    audit.record(
        session,
        actor,
        "clinical_object.corrected",
        "encounter",
        encounter.id,
        from_version=current.object_version,
        to_version=corrected.object_version,
        operations=[op.operation for op in operations],
    )
    # 4. régénération
    if regenerate:
        documents.generate(session, encounter, corrected, providers)
    session.flush()
    return encounter
