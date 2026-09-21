"""Parcours complet via l'API : patient, consultation, pipeline, idempotence."""

from __future__ import annotations

import json
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
    from oris_api.providers.base import ExtractionUnavailable, ProviderInfo

    class Refusing:
        # Le contrat fournisseur exige une identité : c'est elle qui rattache un
        # résultat — ou un refus — à la version qui l'a produit.
        info = ProviderInfo(name="test", version="refusing-1")

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


def test_fixture_consultation_never_reaches_the_configured_stt_provider(api: Any) -> None:
    """L'« enregistrement » d'une consultation fictive est une étiquette, pas du son."""
    from dataclasses import replace

    from oris_api.main import app
    from oris_api.providers.base import ProviderInfo

    class NeverCalled:
        info = ProviderInfo(name="interdit", version="0", capabilities=[])

        async def transcribe(self, chunks: Any, locale: str, glossary: Any) -> Any:
            raise AssertionError("une consultation fictive ne part pas chez un fournisseur")

    original = app.state.providers
    app.state.providers = replace(original, speech_to_text=NeverCalled())
    try:
        encounter = run_synthetic(api, "ORIS-SYN-092")
    finally:
        app.state.providers = original
    assert encounter["status"] == "review"


def test_progress_reports_what_is_really_in_the_database(api: Any) -> None:
    """L'écran d'attente ne doit rien inventer : chaque étape est lue en base (S06)."""
    patient = api.post("/patients", json={"first_name": "Marie", "last_name": "Dupont"}).json()
    created = api.post(
        "/encounters",
        json={"patient_id": patient["id"], "synthetic_case_id": "ORIS-SYN-092"},
    ).json()
    eid = created["id"]

    depart = api.get(f"/encounters/{eid}/progress").json()
    assert depart == {
        "status": "draft",
        "transcript_segments": 0,
        "facts": 0,
        "documents": 0,
        "termine": True,
    }

    api.post(f"/encounters/{eid}/start", json={"patient_informed": True})
    api.post(f"/encounters/{eid}/finish")

    arrivee = api.get(f"/encounters/{eid}/progress").json()
    assert arrivee["status"] == "review"
    assert arrivee["transcript_segments"] > 0
    assert arrivee["facts"] > 0
    assert arrivee["documents"] > 0
    assert arrivee["termine"] is True


def test_the_practitioner_can_rewrite_the_text_without_touching_the_record(api: Any) -> None:
    """§48 : éditer le texte est permis, mais Oris ne fait pas semblant d'en tirer des faits."""
    eid = run_synthetic(api, "ORIS-SYN-092")["id"]
    note = documents_by_type(api, eid)["consultation_note"]
    version_objet = clinical_object(api, eid)["object_version"]

    reecrit = api.post(
        f"/documents/{note['id']}/text",
        json={"content": "Compte rendu réécrit à la main par le praticien."},
    )
    assert reecrit.status_code == 200, reecrit.text
    apres = reecrit.json()
    assert apres["content"] == "Compte rendu réécrit à la main par le praticien."
    assert apres["version"] == note["version"] + 1
    assert apres["generator"] == "practitioner:manual"
    # Aucune provenance inventée sur un texte écrit à la main.
    assert apres["claims"] == [] and apres["supported_fact_ids"] == []
    # Le dossier clinique n'a pas bougé.
    assert clinical_object(api, eid)["object_version"] == version_objet

    evenements = api.get(f"/encounters/{eid}/learning-events").json()
    assert any(event["event_type"] == "document_text_edit" for event in evenements)


def test_rewriting_with_the_same_text_changes_nothing(api: Any) -> None:
    eid = run_synthetic(api, "ORIS-SYN-092")["id"]
    note = documents_by_type(api, eid)["consultation_note"]
    refus = api.post(f"/documents/{note['id']}/text", json={"content": note["content"]})
    assert refus.status_code == 409 and refus.json()["code"] == "NO_CHANGE"


def test_a_marked_moment_is_kept_but_never_becomes_a_clinical_fact(api: Any) -> None:
    """« Marquer un point » (§11) pose un signet, jamais une donnée clinique."""
    patient = api.post("/patients", json={"first_name": "Test", "last_name": "Repère"}).json()
    encounter = api.post(
        "/encounters", json={"patient_id": patient["id"], "synthetic_case_id": "ORIS-SYN-092"}
    ).json()
    eid = encounter["id"]

    # Hors écoute, marquer n'a pas de sens.
    assert api.post(f"/encounters/{eid}/marks", json={"timestamp_ms": 0}).json()["code"] == (
        "INVALID_TRANSITION"
    )

    api.post(f"/encounters/{eid}/start", json={"patient_informed": True})
    assert api.post(f"/encounters/{eid}/marks", json={"timestamp_ms": 12_000}).status_code == 201
    api.post(f"/encounters/{eid}/marks", json={"timestamp_ms": 3_000})
    # Le même instant deux fois ne crée qu'un repère.
    api.post(f"/encounters/{eid}/marks", json={"timestamp_ms": 3_000})

    marks = api.get(f"/encounters/{eid}/marks").json()
    assert [m["timestamp_ms"] for m in marks] == [3_000, 12_000]

    finished = api.post(f"/encounters/{eid}/finish").json()
    assert finished["status"] == "review"
    obj = clinical_object(api, eid)
    # Aucun fait ne provient d'un repère : le dossier est celui du cas fictif seul.
    assert all(fact["source_type"] != "mark" for fact in obj["facts"])
    assert [m["timestamp_ms"] for m in api.get(f"/encounters/{eid}/marks").json()] == [
        3_000,
        12_000,
    ]


def test_the_administrative_note_never_reaches_the_record(api: Any) -> None:
    """La note de la fiche patient (§9) est administrative, jamais clinique.

    Elle aide le praticien à s'organiser. Oris ne la lit pas : elle n'entre ni dans la
    transcription, ni dans les faits, ni dans un document.
    """
    marqueur = "NOTE ADMINISTRATIVE : préfère le matin, allergie latex à confirmer"
    patient = api.post(
        "/patients",
        json={"first_name": "Test", "last_name": "Note", "note": marqueur},
    ).json()
    assert patient["note"] == marqueur

    encounter = api.post(
        "/encounters", json={"patient_id": patient["id"], "synthetic_case_id": "ORIS-SYN-001"}
    ).json()
    eid = encounter["id"]
    api.post(f"/encounters/{eid}/start", json={"patient_informed": True})
    assert api.post(f"/encounters/{eid}/finish").json()["status"] == "review"

    segments = api.get(f"/encounters/{eid}/transcript").json()["segments"]
    assert all(marqueur not in segment["text"] for segment in segments)

    objet = clinical_object(api, eid)
    assert marqueur not in json.dumps(objet, ensure_ascii=False)

    for document in documents_by_type(api, eid).values():
        assert marqueur not in document["content"]

    # Et elle se modifie comme le reste de la fiche.
    modifie = api.patch(f"/patients/{patient['id']}", json={"note": "à rappeler au cabinet"})
    assert modifie.json()["note"] == "à rappeler au cabinet"
    # « Courte » est une contrainte, pas une suggestion : un roman est refusé.
    assert api.patch(f"/patients/{patient['id']}", json={"note": "x" * 501}).status_code == 422


def test_the_smilecloud_case_is_linked_once_and_kept(api: Any) -> None:
    """Le dossier SmileCloud du patient : posé une fois, retenu, détachable.

    Il a son propre champ. `external_id` porte le numéro de dossier du cabinet et ne
    doit pas bouger quand on rattache SmileCloud — sinon on perd l'un des deux.
    """
    patient = api.post(
        "/patients",
        json={"first_name": "Justine", "last_name": "ESSAI", "external_id": "CEM-4412"},
    ).json()
    assert patient["smilecloud_case_id"] is None

    case = "3c9422c4-c1a5-40ca-968a-c6077a9b34b0"
    lie = api.patch(f"/patients/{patient['id']}", json={"smilecloud_case_id": case}).json()
    assert lie["smilecloud_case_id"] == case
    assert lie["external_id"] == "CEM-4412"  # l'autre numéro n'a pas bougé

    # Il se relit tel quel : le lien est posé une fois, pas redemandé.
    assert api.get(f"/patients/{patient['id']}").json()["smilecloud_case_id"] == case

    # « Ce n'était pas le bon dossier » doit pouvoir se dire.
    detache = api.patch(f"/patients/{patient['id']}", json={"smilecloud_case_id": None}).json()
    assert detache["smilecloud_case_id"] is None

    # Un nom collé par erreur dans le champ est refusé, pas rangé « au cas où ».
    refuse = api.patch(f"/patients/{patient['id']}", json={"smilecloud_case_id": "Justine ESSAI"})
    assert refuse.status_code == 422


def test_the_note_can_be_dictated_and_the_sound_is_never_kept(api: Any) -> None:
    """Dicter la note (§9) : transcrire, rendre le texte, oublier le son."""
    import hashlib
    import struct
    from dataclasses import replace
    from typing import ClassVar

    from oris_api.contracts import TranscriptSegment
    from oris_api.domain.types import TranscriptionResult
    from oris_api.main import app
    from oris_api.providers.base import ProviderInfo
    from oris_api.services.audio import AUDIO_FORMAT

    class Dictee:
        info = ProviderInfo(name="test", version="dictee-1")
        recu: ClassVar[list[int]] = []

        async def transcribe(self, chunks: Any, locale: str, glossary: Any) -> Any:
            Dictee.recu.append(len(chunks[0].payload))
            return TranscriptionResult(
                segments=[
                    TranscriptSegment(
                        segment_id="d1",
                        start_ms=0,
                        end_ms=2000,
                        speaker_role="practitioner",
                        text="Préfère les rendez-vous du matin.",
                        confidence=0.9,
                        is_final=True,
                    )
                ],
                gaps=[],
            )

    patient = api.post("/patients", json={"first_name": "Test", "last_name": "Dictée"}).json()
    pcm = struct.pack("<h", 0) * 16_000
    original = app.state.providers
    app.state.providers = replace(original, speech_to_text=Dictee())
    try:
        reponse = api.post(
            f"/patients/{patient['id']}/note/dictation",
            content=pcm,
            headers={"Content-Type": AUDIO_FORMAT},
        )
        assert reponse.status_code == 200, reponse.text
        assert reponse.json()["text"] == "Préfère les rendez-vous du matin."
        assert Dictee.recu == [len(pcm)]

        # Un format refusé ne passe pas.
        refuse = api.post(
            f"/patients/{patient['id']}/note/dictation",
            content=pcm,
            headers={"Content-Type": "audio/mp3"},
        )
        assert refuse.json()["code"] == "UNSUPPORTED_AUDIO_FORMAT"
    finally:
        app.state.providers = original

    # Le son n'est pas devenu une note : c'est le praticien qui enregistre.
    assert api.get(f"/patients/{patient['id']}").json()["note"] == ""
    assert hashlib.sha256(pcm).hexdigest()  # le condensé n'a servi qu'au transport
