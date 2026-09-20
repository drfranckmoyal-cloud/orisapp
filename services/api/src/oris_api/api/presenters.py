"""Conversion des lignes de base en réponses d'API."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from oris_api.api.schemas import (
    ClaimOut,
    DocumentOut,
    DocumentSummary,
    EncounterOut,
    PatientOut,
    PractitionerOut,
    ProcessingError,
    ValidationIssueOut,
)
from oris_api.db.models import (
    DocumentRow,
    DocumentVersion,
    Encounter,
    EncounterObjectVersion,
    Organization,
    Patient,
    User,
)
from oris_api.services import documents


def encounter_out(session: Session, encounter: Encounter) -> EncounterOut:
    patient = session.get(Patient, encounter.patient_id)
    assert patient is not None  # noqa: S101 - clé étrangère non nulle
    praticien = session.get(User, encounter.practitioner_id)
    organisation = session.get(Organization, encounter.organization_id)
    titre = str((organisation.identity or {}).get("practitioner_title", "")) if organisation else ""
    snapshot = (
        session.query(EncounterObjectVersion)
        .filter_by(encounter_id=encounter.id, version=encounter.object_version)
        .one_or_none()
    )
    warnings: list[dict[str, Any]] = snapshot.clinical_object["warnings"] if snapshot else []
    metadata = encounter.metadata_json
    return EncounterOut(
        id=encounter.id,
        patient=PatientOut.model_validate(patient),
        practitioner=PractitionerOut(
            id=encounter.practitioner_id,
            name=praticien.name if praticien else "",
            title=titre,
        ),
        status=encounter.status,
        object_version=encounter.object_version,
        started_at=encounter.started_at,
        ended_at=encounter.ended_at,
        created_at=encounter.created_at,
        synthetic_case_id=metadata.get("synthetic_case_id"),
        mode=encounter.mode,
        processing_errors=[ProcessingError(**e) for e in metadata.get("processing_errors", [])],
        critical_warning_count=sum(1 for w in warnings if w["severity"] == "critical"),
        documents=[
            DocumentSummary(id=d.id, document_type=d.document_type, status=d.status)
            for d in documents.list_documents(session, encounter.id)
        ],
    )


def document_out(
    document: DocumentRow, version: DocumentVersion, current_object_version: int
) -> DocumentOut:
    return DocumentOut(
        id=document.id,
        encounter_id=document.encounter_id,
        document_type=document.document_type,
        status=document.status,
        version=version.version,
        generated_from_object_version=version.generated_from_object_version,
        is_current=version.generated_from_object_version == current_object_version,
        content=version.content,
        claims=[ClaimOut(**claim) for claim in version.claims],
        supported_fact_ids=version.supported_fact_ids,
        validation_issues=[ValidationIssueOut(**issue) for issue in version.validation_issues],
        generator=version.generator,
        created_at=version.created_at,
        validated_at=version.validated_at,
    )
