"""Parcours complet via l'API : patient, consultation, pipeline, idempotence."""

from __future__ import annotations

from typing import Any

from oris_api.contracts import validate_contract
from oris_api.synthetic.corpus import default_corpus
from tests.conftest import clinical_object, documents_by_type, run_synthetic


def test_patient_crud(api: Any) -> None:
    created = api.post("/patients", json={"first_name": "Léa", "last_name": "Fictive"})
    assert created.status_code == 201
    patient_id = created.json()["id"]
    assert api.get(f"/patients/{patient_id}").json()["last_name"] == "Fictive"
    patched = api.patch(f"/patients/{patient_id}", json={"first_name": "Léna"})
    assert patched.json()["first_name"] == "Léna"
    assert [p["id"] for p in api.get("/patients", params={"q": "fict"}).json()] == [patient_id]
    assert api.get("/patients/00000000-0000-0000-0000-000000000000").status_code == 404


def test_all_100_synthetic_consultations_reach_review_with_valid_objects(api: Any) -> None:
    for case in default_corpus().cases():
        encounter = run_synthetic(api, case.case_id)
        assert encounter["status"] == "review", (case.case_id, encounter["processing_errors"])
        obj = clinical_object(api, encounter["id"])
        validate_contract("ClinicalEncounter", obj)
        assert [f["fact_id"] for f in obj["facts"]] == [f.fact_id for f in case.facts]
        assert [w["code"] for w in obj["warnings"]] == list(case.expected_warning_codes)
        docs = documents_by_type(api, encounter["id"])
        assert "consultation_note" in docs
        assert ("treatment_plan_text" in docs) == bool(
            case.treatment_plan and case.treatment_plan.items
        )
        for doc in docs.values():
            assert doc["status"] == "draft_ai", (case.case_id, doc["validation_issues"])
            assert all(c["fact_ids"] or c["warning_codes"] for c in doc["claims"])


def test_manual_lifecycle_and_idempotent_processing(api: Any) -> None:
    patient = api.post("/patients", json={"first_name": "Test", "last_name": "Cycle"}).json()
    encounter = api.post(
        "/encounters", json={"patient_id": patient["id"], "synthetic_case_id": "ORIS-SYN-092"}
    ).json()
    eid = encounter["id"]
    assert encounter["status"] == "draft"
    assert api.post(f"/encounters/{eid}/finish").json()["code"] == "INVALID_TRANSITION"
    refused = api.post(f"/encounters/{eid}/start")
    assert refused.json()["code"] == "PATIENT_INFORMATION_REQUIRED"
    started = api.post(f"/encounters/{eid}/start", json={"patient_informed": True})
    assert started.json()["status"] == "recording"
    for action, status in [("pause", "paused"), ("resume", "recording")]:
        assert api.post(f"/encounters/{eid}/{action}").json()["status"] == status
    finished = api.post(f"/encounters/{eid}/finish").json()
    assert finished["status"] == "review"
    assert finished["object_version"] == 1
    # Relancer le traitement ne duplique rien.
    again = api.post(f"/encounters/{eid}/process").json()
    assert again["object_version"] == 1
    versions = api.get(f"/encounters/{eid}/clinical-object").json()["versions"]
    assert [v["version"] for v in versions] == [1]
    assert len(api.get(f"/encounters/{eid}/transcript").json()["segments"]) == 2


def test_consultation_without_audio_fails_visibly_and_can_be_retried(api: Any) -> None:
    patient = api.post("/patients", json={"first_name": "Test", "last_name": "Muet"}).json()
    eid = api.post("/encounters", json={"patient_id": patient["id"]}).json()["id"]
    api.post(f"/encounters/{eid}/start", json={"patient_informed": True})
    failed = api.post(f"/encounters/{eid}/finish").json()
    assert failed["status"] == "transcription_failed"
    assert failed["processing_errors"][0]["rule"] == "NO_TRANSCRIPT"
    assert api.get(f"/encounters/{eid}/documents").json() == []
    assert api.post(f"/encounters/{eid}/process").json()["status"] == "transcription_failed"
    assert len(api.get("/encounters").json()) == 1


def test_unknown_synthetic_case_is_404(api: Any) -> None:
    response = api.post("/synthetic-cases/ORIS-SYN-999/encounters")
    assert response.status_code == 404
    assert response.json()["code"] == "SYNTHETIC_CASE_NOT_FOUND"


def test_projection_tables_match_current_object(api: Any, migrated_engine: Any) -> None:
    from sqlalchemy import text

    eid = run_synthetic(api, "ORIS-SYN-051")["id"]
    with migrated_engine.connect() as connection:
        facts = connection.execute(
            text("SELECT count(*) FROM clinical_facts WHERE encounter_id = :e"), {"e": eid}
        ).scalar_one()
        links = connection.execute(
            text(
                "SELECT count(*) FROM procedure_evidence pe "
                "JOIN procedures p ON p.id = pe.procedure_id WHERE p.encounter_id = :e"
            ),
            {"e": eid},
        ).scalar_one()
    obj = clinical_object(api, eid)
    assert facts == len(obj["facts"])
    assert links == len(obj["procedures"][0]["evidence_fact_ids"])


def test_extraction_failure_is_an_explicit_failed_consultation_not_a_crash(api: Any) -> None:
    """Un fournisseur qui refuse sa propre sortie ne fait pas tomber la consultation."""
    import dataclasses

    from oris_api.main import app
    from oris_api.providers.base import ExtractionUnavailable

    class Refusing:
        info = None

        async def extract(self, segments: Any, glossary: Any) -> Any:
            raise ExtractionUnavailable(
                "EXTRACTION_INVALID_OUTPUT",
                details="règles cliniques non respectées : PROCEDURE_STATUS_UNSUPPORTED (pr1)",
            )

    original = app.state.providers
    app.state.providers = dataclasses.replace(original, clinical_extraction=Refusing())
    try:
        patient = api.post("/patients", json={"first_name": "Test", "last_name": "Refus"}).json()
        eid = api.post(
            "/encounters", json={"patient_id": patient["id"], "synthetic_case_id": "ORIS-SYN-092"}
        ).json()["id"]
        api.post(f"/encounters/{eid}/start", json={"patient_informed": True})
        failed = api.post(f"/encounters/{eid}/finish").json()
    finally:
        app.state.providers = original

    assert failed["status"] == "generation_failed"
    # La raison du refus est visible, sous forme de règle, sans contenu clinique.
    assert [e["rule"] for e in failed["processing_errors"]] == ["PROCEDURE_STATUS_UNSUPPORTED"]
    assert api.get(f"/encounters/{eid}/documents").json() == []
