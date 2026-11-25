"""Déposer un document dans le dossier Veasy du patient (Franck, 25/11/2026).

Ce que ces tests tiennent :
- seul un document validé part ;
- une demande par document, servie à l'extension avec de quoi retrouver le dossier ;
- l'extension retire le PDF, le dépose, et le dit ; le numéro Veasy est retenu ;
- un contretemps garde la demande ouverte ; un refus la ferme et se dit.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest

from tests.conftest import documents_by_type, run_synthetic


@pytest.fixture(autouse=True)
def file_vide() -> None:
    """Chaque essai part d'une file de dépôts vide."""
    for fichier in ("demandes.json", "dossiers.json"):
        (Path(os.environ["VEASY_DIR"]) / fichier).unlink(missing_ok=True)


def _note_validee(api: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    encounter = run_synthetic(api, "ORIS-SYN-092")
    note = documents_by_type(api, encounter["id"])["consultation_note"]
    return encounter, note


def test_a_validated_document_goes_to_veasy_and_teaches_the_patient_number(api: Any) -> None:
    encounter, note = _note_validee(api)
    pid = encounter["patient"]["id"]

    # Sans dossier Veasy vérifié, rien ne part : le dossier se relie d'abord.
    non_relie = api.post(f"/documents/{note['id']}/veasy")
    assert (non_relie.status_code, non_relie.json()["code"]) == (422, "VEASY_NON_RELIE")
    api.put(f"/patients/{pid}/veasy", json={"veasy_id": "123456"})

    brouillon = api.post(f"/documents/{note['id']}/veasy")
    assert (brouillon.status_code, brouillon.json()["code"]) == (422, "DOCUMENT_NOT_VALIDATED")
    assert api.get(f"/documents/{note['id']}/veasy").json()["etat"] == "absent"

    api.post(f"/documents/{note['id']}/validate", json={"acknowledged_warning_codes": []})
    assert api.post(f"/documents/{note['id']}/veasy").json()["etat"] == "en_attente"
    api.post(f"/documents/{note['id']}/veasy")  # redemander ne fait pas deux dépôts

    (demande,) = api.get("/veasy/demandes").json()
    assert demande["nom_fichier"].endswith(".pdf")
    assert demande["patient"]["nom"] == encounter["patient"]["last_name"]
    assert demande["patient"]["veasy_id"] == "123456"
    assert "patient_id" not in demande and "organisation_id" not in demande

    pdf = api.get(f"/veasy/depot/{demande['id']}")
    assert (pdf.status_code, pdf.content[:4]) == (200, b"%PDF")
    fait = api.post("/veasy/depose", json={"id": demande["id"], "veasy_patient_id": "123456"})
    assert fait.json() == {"note": True}

    assert api.get(f"/documents/{note['id']}/veasy").json()["etat"] == "depose"
    assert api.get("/veasy/demandes").json() == []
    # Le dépôt suivant ira droit au dossier.
    api.post(f"/documents/{note['id']}/veasy")
    (suivante,) = api.get("/veasy/demandes").json()
    assert suivante["patient"]["veasy_id"] == "123456"
    assert pid


def test_a_contretemps_keeps_the_request_open_and_a_refusal_closes_it(api: Any) -> None:
    encounter, note = _note_validee(api)
    api.put(f"/patients/{encounter['patient']['id']}/veasy", json={"veasy_id": "42"})
    api.post(f"/documents/{note['id']}/validate", json={"acknowledged_warning_codes": []})
    api.post(f"/documents/{note['id']}/veasy")
    (demande,) = api.get("/veasy/demandes").json()

    api.post(
        "/veasy/depose",
        json={"id": demande["id"], "raison": "page Veasy pas prête", "reessayer": True},
    )
    etat = api.get(f"/documents/{note['id']}/veasy").json()
    assert (etat["etat"], etat["raison"]) == ("en_attente", "page Veasy pas prête")
    assert api.get("/veasy/demandes").json()[0]["essais"] == 1

    api.post(
        "/veasy/depose",
        json={"id": demande["id"], "raison": "patient introuvable dans Veasy"},
    )
    etat = api.get(f"/documents/{note['id']}/veasy").json()
    assert (etat["etat"], etat["raison"]) == ("impossible", "patient introuvable dans Veasy")
    assert api.get("/veasy/demandes").json() == []


def test_an_unknown_request_is_refused(api: Any) -> None:
    assert api.post("/veasy/depose", json={"id": "inconnue"}).status_code == 404
    assert api.get("/veasy/depot/inconnue").status_code == 404


def test_the_veasy_file_is_matched_then_confirmed_like_smilecloud(api: Any) -> None:
    """« Une vérification de matching des dossiers comme pour SmileCloud » (25/11/2026)."""
    encounter, _ = _note_validee(api)
    pid = encounter["patient"]["id"]
    nom = f"{encounter['patient']['last_name']} {encounter['patient']['first_name']}"

    assert api.get(f"/patients/{pid}/veasy").json()["etat"] == "sans_liste"

    livre = api.post(
        "/veasy/dossiers",
        json={
            "dossiers": [
                {"veasy_id": "777", "nom": nom, "date_naissance": "1980-01-02"},
                {"veasy_id": "888", "nom": "AUTRE Personne"},
                {"veasy_id": "pas-un-numero", "nom": "IGNORE Moi"},
            ]
        },
    )
    assert livre.json() == {"dossiers": 2}

    vue = api.get(f"/patients/{pid}/veasy").json()
    assert vue["etat"] == "trouve"
    assert [(c["veasy_id"], c["date_naissance"]) for c in vue["candidats"]] == [
        ("777", "1980-01-02")
    ]

    relie = api.put(f"/patients/{pid}/veasy", json={"veasy_id": "777"}).json()
    assert (relie["etat"], relie["nom"]) == ("relie", nom)
    assert api.put(f"/patients/{pid}/veasy", json={"veasy_id": "abc"}).status_code == 422
    assert api.put(f"/patients/{pid}/veasy", json={"veasy_id": None}).json()["etat"] == "trouve"
