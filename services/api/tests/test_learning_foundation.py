"""Infrastructure d'apprentissage exigée dès la fondation (spec §56, §202, §205).

Ce que ces tests tiennent :
- un traitement laisse une trace de ce qui a tourné, et cette trace ne contient
  aucun contenu patient ;
- le profil d'apprentissage reflète les préférences et le dictionnaire, sans jamais
  rien ajouter de clinique ;
- une mesure cite son jeu de données, et la porte de sortie se ferme sur une
  régression critique.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select

from oris_api.db.models import (
    DatasetVersion,
    EvaluationRun,
    ModelRun,
    ModelVersion,
    PromptVersion,
)
from oris_api.services import registry
from tests.conftest import run_synthetic


def test_a_consultation_leaves_the_trace_of_what_actually_ran(api: Any, db_session: Any) -> None:
    eid = run_synthetic(api, "ORIS-SYN-001")["id"]

    runs = registry.runs_for(db_session, UUID(eid))
    composants = [run.component for run in runs]
    assert composants == ["speech_to_text", "clinical_extraction"]
    assert all(run.status == "succeeded" for run in runs)
    assert all(run.latency_ms is not None and run.latency_ms >= 0 for run in runs)

    # La version qui a tourné est rattachée, pas devinée.
    extraction = runs[-1]
    assert extraction.model_version_id is not None
    assert extraction.prompt_version_id is not None
    invite = db_session.get(PromptVersion, extraction.prompt_version_id)
    assert invite.component == "clinical_extraction"
    assert len(invite.content_hash) == 64
    modele = db_session.get(ModelVersion, extraction.model_version_id)
    assert modele.component == "clinical_extraction"


def test_the_trace_never_holds_patient_content(api: Any, db_session: Any) -> None:
    """« Ne jamais y stocker de contenu patient en clair » (§56, dernière ligne)."""
    eid = run_synthetic(api, "ORIS-SYN-001")["id"]
    transcript = api.get(f"/encounters/{eid}/transcript").json()["segments"]
    paroles = [segment["text"] for segment in transcript]
    assert paroles, "le cas fictif doit produire du texte, sinon le test ne prouve rien"

    runs = db_session.scalars(select(ModelRun)).all()
    ecrit = " ".join(
        f"{run.component} {run.status} {run.error_code or ''} {run.counters}" for run in runs
    )
    for parole in paroles:
        assert parole not in ecrit
    # Seuls des nombres sont comptés.
    for run in runs:
        assert all(isinstance(valeur, int) for valeur in run.counters.values())


def test_a_failed_provider_is_traced_too(api: Any, db_session: Any) -> None:
    """Une panne se lit dans la trace : c'est elle qui fera la différence plus tard."""
    patient = api.post("/patients", json={"first_name": "Test", "last_name": "Panne"}).json()
    eid = api.post("/encounters", json={"patient_id": patient["id"]}).json()["id"]
    api.post(f"/encounters/{eid}/start", json={"patient_informed": True})
    assert api.post(f"/encounters/{eid}/finish").json()["status"] == "transcription_failed"

    runs = registry.runs_for(db_session, UUID(eid))
    assert [run.status for run in runs] == ["failed"]
    assert runs[0].component == "speech_to_text"
    assert runs[0].error_code


def test_the_learning_profile_mirrors_preferences_and_never_invents(api: Any) -> None:
    depart = api.get("/me/learning/profile").json()
    assert depart["preferred_document_length"] == "standard"
    assert depart["preferred_terms"] == {}
    assert depart["frequent_materials"] == []

    api.patch("/me/preferences", json={"document_length": "concise"})
    api.patch("/me/preferences", json={"terminology": {"extraction": "avulsion"}})
    api.post(
        "/glossary",
        json={
            "canonical": "G-ænial A'CHORD",
            "aliases": ["genial accord"],
            "category": "material",
        },
    )

    profil = api.get("/me/learning/profile").json()
    assert profil["preferred_document_length"] == "short"
    assert profil["preferred_terms"] == {"extraction": "avulsion"}
    assert profil["frequent_materials"] == ["G-ænial A'CHORD"]
    assert profil["speech_aliases"] == [{"heard": "genial accord", "canonical": "G-ænial A'CHORD"}]
    # Un terme désactivé sort du profil : l'apprentissage est réversible (§177).
    term_id = api.get("/glossary").json()[0]["id"]
    api.patch(f"/glossary/{term_id}", json={"status": "disabled"})
    assert api.get("/me/learning/profile").json()["frequent_materials"] == []


def test_the_engine_versions_report_what_ran_not_what_is_configured(api: Any) -> None:
    assert api.get("/system/versions").json() == []
    run_synthetic(api, "ORIS-SYN-001")
    versions = api.get("/system/versions").json()
    composants = {item["component"] for item in versions}
    assert composants == {"speech_to_text", "clinical_extraction"}
    extraction = next(item for item in versions if item["component"] == "clinical_extraction")
    assert extraction["prompt_version"]
    assert extraction["model_id"]


def test_a_measure_cites_its_dataset_and_the_gate_closes_on_a_regression(
    db_session: Any,
) -> None:  # `db_session` apporte une base propre
    registry.dataset_version(
        db_session, "oris-synthetic-consultations", "100", item_count=100, nature="synthetic"
    )
    # Le même jeu déclaré deux fois reste une seule ligne.
    registry.dataset_version(db_session, "oris-synthetic-consultations", "100", item_count=100)
    assert len(db_session.scalars(select(DatasetVersion)).all()) == 1

    passe = registry.record_evaluation(
        db_session,
        component="clinical_extraction",
        candidate_version="claude-sonnet-5/extraction-fr-5",
        dataset="oris-synthetic-consultations@100",
        metrics={"fact_recall": 0.97},
        critical_regressions=[],
    )
    assert passe.release_gate_passed is True

    bloque = registry.record_evaluation(
        db_session,
        component="clinical_extraction",
        candidate_version="candidat-suivant",
        dataset="oris-synthetic-consultations@100",
        metrics={"fact_recall": 0.99},
        critical_regressions=["ORIS-SYN-014 : négation perdue"],
    )
    # Une meilleure moyenne n'ouvre pas la porte si un cas critique a régressé.
    assert bloque.release_gate_passed is False
    assert len(db_session.scalars(select(EvaluationRun)).all()) == 2


def test_a_silent_prompt_change_is_visible(db_session: Any) -> None:
    """Changer le texte sans changer la version se voit à l'empreinte."""
    avant = registry.prompt_version(db_session, "clinical_extraction", "essai-1", "consigne A")
    empreinte = avant.content_hash
    apres = registry.prompt_version(db_session, "clinical_extraction", "essai-1", "consigne B")
    assert apres.id == avant.id
    assert apres.content_hash != empreinte
