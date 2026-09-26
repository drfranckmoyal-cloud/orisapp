"""Persistance de l'objet clinique versionné.

- `encounter_object_versions` : l'objet complet par version, jamais modifié.
- tables `clinical_facts`, `treatment_plans`, `procedures` et liens de preuve :
  projection de la version courante, reconstruite à chaque nouvelle version.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from oris_api.contracts import ClinicalEncounter, TranscriptSegment, validate_contract
from oris_api.db.models import (
    ClinicalFactRow,
    Encounter,
    EncounterObjectVersion,
    FactEvidenceLink,
    ObjectChangeKind,
    ProcedureEvidence,
    ProcedureRow,
    TranscriptSegmentRow,
    TreatmentPlanItemEvidence,
    TreatmentPlanItemRow,
    TreatmentPlanRow,
)
from oris_api.services.errors import Conflict, NotFound


def load_segments(session: Session, encounter_id: UUID) -> list[TranscriptSegment]:
    rows = session.scalars(
        select(TranscriptSegmentRow)
        .where(TranscriptSegmentRow.encounter_id == encounter_id)
        .order_by(TranscriptSegmentRow.start_ms, TranscriptSegmentRow.segment_id)
    )
    return [
        TranscriptSegment(
            segment_id=row.segment_id,
            start_ms=row.start_ms,
            end_ms=row.end_ms,
            speaker_role=row.speaker_role,
            text=row.text,
            confidence=row.confidence,
            is_final=row.is_final,
        )
        for row in rows
    ]


def replace_segments(
    session: Session, encounter_id: UUID, segments: list[TranscriptSegment]
) -> None:
    """Idempotent : un nouveau traitement remplace le transcript précédent."""
    session.execute(
        delete(TranscriptSegmentRow).where(TranscriptSegmentRow.encounter_id == encounter_id)
    )
    session.add_all(
        TranscriptSegmentRow(encounter_id=encounter_id, **segment.model_dump())
        for segment in segments
    )
    session.flush()


def load_current(session: Session, encounter: Encounter) -> ClinicalEncounter:
    row = session.scalar(
        select(EncounterObjectVersion).where(
            EncounterObjectVersion.encounter_id == encounter.id,
            EncounterObjectVersion.version == encounter.object_version,
        )
    )
    if row is None:
        raise NotFound("CLINICAL_OBJECT_NOT_FOUND", str(encounter.id))
    current = ClinicalEncounter.model_validate(row.clinical_object)
    # Le statut vit sur la consultation ; l'instantané garde celui de sa création.
    return current.model_copy(update={"status": encounter.status})


def load_version(session: Session, encounter_id: UUID, version: int) -> ClinicalEncounter | None:
    """L'objet tel qu'il était à cette version — celle qui a servi à écrire un document.

    Un document rédigé avant une correction doit montrer les faits de *son* époque :
    sinon la preuve ne correspond plus à la phrase (§30).
    """
    row = session.scalar(
        select(EncounterObjectVersion).where(
            EncounterObjectVersion.encounter_id == encounter_id,
            EncounterObjectVersion.version == version,
        )
    )
    return None if row is None else ClinicalEncounter.model_validate(row.clinical_object)


def list_versions(session: Session, encounter_id: UUID) -> list[EncounterObjectVersion]:
    return list(
        session.scalars(
            select(EncounterObjectVersion)
            .where(EncounterObjectVersion.encounter_id == encounter_id)
            .order_by(EncounterObjectVersion.version)
        )
    )


def save_version(
    session: Session,
    encounter: Encounter,
    clinical_object: ClinicalEncounter,
    change_kind: ObjectChangeKind,
    created_by: UUID | None,
) -> None:
    payload = clinical_object.model_dump(mode="json")
    validate_contract("ClinicalEncounter", payload)
    exists = session.scalar(
        select(EncounterObjectVersion.id).where(
            EncounterObjectVersion.encounter_id == encounter.id,
            EncounterObjectVersion.version == clinical_object.object_version,
        )
    )
    if exists is not None:
        raise Conflict("OBJECT_VERSION_EXISTS", str(encounter.id))
    session.add(
        EncounterObjectVersion(
            encounter_id=encounter.id,
            version=clinical_object.object_version,
            clinical_object=payload,
            change_kind=change_kind,
            created_by=created_by,
        )
    )
    encounter.object_version = clinical_object.object_version
    rebuild_projection(session, encounter.id, clinical_object)


def rebuild_projection(session: Session, encounter_id: UUID, obj: ClinicalEncounter) -> None:
    session.execute(delete(ClinicalFactRow).where(ClinicalFactRow.encounter_id == encounter_id))
    session.execute(delete(TreatmentPlanRow).where(TreatmentPlanRow.encounter_id == encounter_id))
    session.execute(delete(ProcedureRow).where(ProcedureRow.encounter_id == encounter_id))
    session.flush()

    segment_rows = {
        row.segment_id: row.id
        for row in session.scalars(
            select(TranscriptSegmentRow).where(TranscriptSegmentRow.encounter_id == encounter_id)
        )
    }
    fact_rows: dict[str, UUID] = {}
    for fact in obj.facts:
        row = ClinicalFactRow(
            encounter_id=encounter_id,
            **fact.model_dump(mode="json", exclude={"evidence_segment_ids"}),
        )
        session.add(row)
        session.flush()
        fact_rows[fact.fact_id] = row.id
        for segment_id in fact.evidence_segment_ids:
            if segment_id in segment_rows:
                session.add(
                    FactEvidenceLink(fact_id=row.id, transcript_segment_id=segment_rows[segment_id])
                )

    if obj.treatment_plan is not None:
        plan = obj.treatment_plan
        plan_row = TreatmentPlanRow(
            encounter_id=encounter_id,
            plan_id=plan.plan_id,
            status=plan.status,
            goals=plan.goals,
            notes=plan.notes,
        )
        session.add(plan_row)
        session.flush()
        for item in plan.items:
            item_row = TreatmentPlanItemRow(
                plan_id=plan_row.id, **item.model_dump(mode="json", exclude={"evidence_fact_ids"})
            )
            session.add(item_row)
            session.flush()
            for fact_id in item.evidence_fact_ids:
                session.add(
                    TreatmentPlanItemEvidence(item_id=item_row.id, fact_id=fact_rows[fact_id])
                )

    for procedure in obj.procedures:
        procedure_row = ProcedureRow(
            encounter_id=encounter_id,
            **procedure.model_dump(mode="json", exclude={"evidence_fact_ids"}),
        )
        session.add(procedure_row)
        session.flush()
        for fact_id in procedure.evidence_fact_ids:
            session.add(
                ProcedureEvidence(procedure_id=procedure_row.id, fact_id=fact_rows[fact_id])
            )
    session.flush()
