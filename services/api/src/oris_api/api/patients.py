"""Routes patients (spec §58)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, status

from oris_api.api.dependencies import ActorDep, SessionDep
from oris_api.api.schemas import PatientCreate, PatientOut, PatientUpdate
from oris_api.services import patients

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("", response_model=list[PatientOut])
def list_patients(session: SessionDep, actor: ActorDep, q: str | None = None) -> list[PatientOut]:
    return [PatientOut.model_validate(p) for p in patients.list_patients(session, actor, q)]


@router.post("", response_model=PatientOut, status_code=status.HTTP_201_CREATED)
def create_patient(body: PatientCreate, session: SessionDep, actor: ActorDep) -> PatientOut:
    patient = patients.create_patient(session, actor, **body.model_dump())
    return PatientOut.model_validate(patient)


@router.get("/{patient_id}", response_model=PatientOut)
def get_patient(patient_id: UUID, session: SessionDep, actor: ActorDep) -> PatientOut:
    return PatientOut.model_validate(patients.get_patient(session, actor, patient_id))


@router.patch("/{patient_id}", response_model=PatientOut)
def update_patient(
    patient_id: UUID, body: PatientUpdate, session: SessionDep, actor: ActorDep
) -> PatientOut:
    changes = body.model_dump(exclude_unset=True)
    return PatientOut.model_validate(patients.update_patient(session, actor, patient_id, changes))
