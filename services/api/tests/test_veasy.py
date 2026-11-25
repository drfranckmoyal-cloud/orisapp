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
    for fichier in ("demandes.json", "dossiers.json", "controles.json"):
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

    assert api.get(f"/documents/{note['id']}/veasy").json()["pris_le"] is None
    pdf = api.get(f"/veasy/depot/{demande['id']}")
    assert (pdf.status_code, pdf.content[:4]) == (200, b"%PDF")
    # La barre d'état le sait : l'extension a pris le document, le dépôt est en route.
    en_route = api.get(f"/documents/{note['id']}/veasy").json()
    assert (en_route["etat"], en_route["pris_le"] is not None) == ("en_attente", True)
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
    api.put(f"/patients/{encounter['patient']['id']}/veasy", json={"veasy_id": "12344249"})
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
                {"veasy_id": "13005043", "nom": nom, "date_naissance": "1980-01-02"},
                {"veasy_id": "22222222", "nom": "AUTRE Personne"},
                {"veasy_id": "pas-un-numero", "nom": "IGNORE Moi"},
            ]
        },
    )
    assert livre.json() == {"dossiers": 2}

    vue = api.get(f"/patients/{pid}/veasy").json()
    assert vue["etat"] == "trouve"
    assert [(c["veasy_id"], c["date_naissance"]) for c in vue["candidats"]] == [
        ("13005043", "1980-01-02")
    ]

    relie = api.put(f"/patients/{pid}/veasy", json={"veasy_id": "13005043"}).json()
    assert (relie["etat"], relie["nom"]) == ("relie", nom)
    assert api.put(f"/patients/{pid}/veasy", json={"veasy_id": "abc"}).status_code == 422
    # Le numéro de dossier affiché entre parenthèses n'est pas celui de la fiche.
    assert api.put(f"/patients/{pid}/veasy", json={"veasy_id": "001001016896"}).status_code == 422
    assert api.put(f"/patients/{pid}/veasy", json={"veasy_id": None}).json()["etat"] == "trouve"


def test_the_extension_links_a_sure_match_without_a_click_and_brings_the_email(
    api: Any,
) -> None:
    """« Le rattachement Veasy est inefficace » (Franck, 26/11/2026) : l'extension relie
    elle-même ce qui est sûr, et rapporte le courriel de la fiche Veasy."""
    sur = api.post(
        "/patients",
        json={"first_name": "Justine", "last_name": "DROIT", "birth_date": "1984-03-02"},
    ).json()
    sans_date = api.post("/patients", json={"first_name": "Paul", "last_name": "SANSDATE"}).json()
    douteux = api.post("/patients", json={"first_name": "Ali", "last_name": "DOUTE"}).json()
    api.put(f"/patients/{douteux['id']}/veasy", json={"veasy_id": "12344249"})
    saisi = api.post(
        "/patients",
        json={"first_name": "Eve", "last_name": "SAISIE", "email": "eve@cabinet.example"},
    ).json()

    a_relier = {p["patient_id"]: p for p in api.get("/veasy/a-relier").json()}
    assert {sur["id"], sans_date["id"], douteux["id"], saisi["id"]} <= set(a_relier)
    assert a_relier[sur["id"]]["date_naissance"] == "1984-03-02"
    assert a_relier[douteux["id"]]["veasy_id"] == "12344249"

    reponse = api.post(
        "/veasy/relies",
        json={
            "relies": [
                {
                    "patient_id": sur["id"],
                    "statut": "relie",
                    "veasy_id": "13005043",
                    "email": "justine@example.org",
                },
                {"patient_id": sans_date["id"], "statut": "sans_naissance"},
                {"patient_id": douteux["id"], "statut": "lien_douteux"},
                {
                    "patient_id": saisi["id"],
                    "statut": "relie",
                    "veasy_id": "11111111",
                    "email": "autre@example.org",
                },
            ]
        },
    ).json()
    assert reponse == {"notes": 4, "relies": 2}

    lien = api.get(f"/patients/{sur['id']}/veasy").json()
    assert (lien["etat"], lien["veasy_id"], lien["controle"]["statut"]) == (
        "relie",
        "13005043",
        "relie",
    )
    assert api.get(f"/patients/{sur['id']}").json()["email"] == "justine@example.org"
    # Le lien douteux est retiré, et le praticien le voit.
    vu = api.get(f"/patients/{douteux['id']}/veasy").json()
    assert (vu["veasy_id"], vu["controle"]["statut"]) == (None, "lien_douteux")
    # Une adresse saisie par le praticien n'est jamais écrasée.
    assert api.get(f"/patients/{saisi['id']}").json()["email"] == "eve@cabinet.example"
    # Les patients contrôlés ne reviennent pas au lot suivant.
    restants = {p["patient_id"] for p in api.get("/veasy/a-relier").json()}
    assert sur["id"] not in restants and sans_date["id"] not in restants
