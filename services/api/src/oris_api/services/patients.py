"""Patients (fictifs en développement)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from oris_api.db.models import Encounter, Patient
from oris_api.services import audit
from oris_api.services.errors import NotFound
from oris_api.services.identity import Actor


def list_patients(session: Session, actor: Actor, query: str | None = None) -> list[Patient]:
    statement = select(Patient).where(Patient.organization_id == actor.organization_id)
    if query:
        pattern = f"%{query.strip()}%"
        statement = statement.where(
            or_(Patient.last_name.ilike(pattern), Patient.first_name.ilike(pattern))
        )
    return list(session.scalars(statement.order_by(Patient.last_name, Patient.first_name)))


@dataclass(frozen=True, slots=True)
class Resume:
    """Ce qu'on sait d'un patient sans ouvrir son dossier."""

    consultations: int = 0
    derniere: datetime | None = None
    a_relire: int = 0


def resumes(session: Session, actor: Actor) -> dict[UUID, Resume]:
    """Combien de consultations par patient, la dernière, et ce qui attend une relecture.

    Une seule requête groupée, pas une par ligne : la liste en affiche vingt à la fois.
    """
    lignes = session.execute(
        select(
            Encounter.patient_id,
            func.count(Encounter.id),
            func.max(func.coalesce(Encounter.started_at, Encounter.created_at)),
            func.count(Encounter.id).filter(Encounter.status == "review"),
        )
        .where(Encounter.organization_id == actor.organization_id)
        .group_by(Encounter.patient_id)
    )
    return {
        patient_id: Resume(consultations=total, derniere=derniere, a_relire=a_relire)
        for patient_id, total, derniere, a_relire in lignes
    }


def get_patient(session: Session, actor: Actor, patient_id: UUID) -> Patient:
    patient = session.get(Patient, patient_id)
    if patient is None or patient.organization_id != actor.organization_id:
        raise NotFound("PATIENT_NOT_FOUND", str(patient_id))
    return patient


def create_patient(
    session: Session,
    actor: Actor,
    first_name: str,
    last_name: str,
    birth_date: date | None = None,
    external_id: str | None = None,
    email: str = "",
    note: str = "",
) -> Patient:
    patient = Patient(
        organization_id=actor.organization_id,
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        birth_date=birth_date,
        external_id=external_id,
        email=email.strip(),
        note=note.strip(),
    )
    session.add(patient)
    session.flush()
    audit.record(session, actor, "patient.created", "patient", patient.id)
    return patient


def update_patient(
    session: Session, actor: Actor, patient_id: UUID, changes: dict[str, object]
) -> Patient:
    patient = get_patient(session, actor, patient_id)
    for field, value in changes.items():
        setattr(patient, field, value.strip() if isinstance(value, str) else value)
    audit.record(session, actor, "patient.updated", "patient", patient.id, fields=sorted(changes))
    session.flush()
    return patient
