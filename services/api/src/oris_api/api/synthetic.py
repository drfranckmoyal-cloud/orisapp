"""Consultations synthétiques (développement uniquement : `local` et `test`)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import select

from oris_api.api.dependencies import ActorDep, ProvidersDep, SessionDep, SinkDep
from oris_api.api.presenters import encounter_out
from oris_api.api.schemas import EncounterOut, SyntheticCaseOut
from oris_api.config import Settings, get_settings
from oris_api.db.models import Patient
from oris_api.services import encounters, patients
from oris_api.services.errors import Forbidden, NotFound
from oris_api.synthetic.corpus import SyntheticCorpus, default_corpus

router = APIRouter(prefix="/synthetic-cases", tags=["synthetic"])


def corpus(settings: Annotated[Settings, Depends(get_settings)]) -> SyntheticCorpus:
    if settings.app_env not in {"local", "test"}:
        raise Forbidden("SYNTHETIC_CORPUS_DISABLED")
    return default_corpus()


CorpusDep = Annotated[SyntheticCorpus, Depends(corpus)]


@router.get("", response_model=list[SyntheticCaseOut])
def list_cases(corpus: CorpusDep, actor: ActorDep) -> list[SyntheticCaseOut]:
    return [
        SyntheticCaseOut(
            case_id=case.case_id,
            domain=case.domain,
            tags=list(case.tags),
            patient_first_name=case.patient_first_name,
            patient_last_name=case.patient_last_name,
            segment_count=len(case.segments),
        )
        for case in corpus.cases()
    ]


@router.post(
    "/{case_id}/encounters", response_model=EncounterOut, status_code=status.HTTP_201_CREATED
)
def run_case(
    case_id: str,
    corpus: CorpusDep,
    session: SessionDep,
    actor: ActorDep,
    providers: ProvidersDep,
    sink: SinkDep,
) -> EncounterOut:
    """Consultation complète en un appel : patient fictif, démarrage, fin, traitement."""
    case = corpus.get(case_id)
    if case is None:
        raise NotFound("SYNTHETIC_CASE_NOT_FOUND", case_id)
    patient = session.scalar(
        select(Patient).where(
            Patient.organization_id == actor.organization_id,
            Patient.first_name == case.patient_first_name,
            Patient.last_name == case.patient_last_name,
        )
    ) or patients.create_patient(session, actor, case.patient_first_name, case.patient_last_name)
    encounter = encounters.create_encounter(session, actor, patient.id, case.case_id)
    encounters.transition(session, actor, encounter, "recording")
    encounters.finish(session, actor, encounter, providers, sink)
    return encounter_out(session, encounter)
