"""Agenda du jour, lu chez Dental Lens (écran « Votre journée »).

Ce que ces tests tiennent :
- Oris préfère le serveur Dental Lens, mais sait se passer de lui ;
- une journée que personne n'a déposée est dite absente, jamais inventée ;
- un patient déjà connu d'Oris est reconnu malgré la casse et les accents ;
- **lire l'agenda ne crée aucun dossier** : rien n'entre en base sans un geste.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from oris_api.config import Settings
from oris_api.services import agenda

JOUR = "2026-09-22"


def reglages(tmp_path: Path, **extra: Any) -> Settings:
    return Settings(
        agenda_provider="dental_lens",
        dental_lens_registre=tmp_path,
        dental_lens_url="http://127.0.0.1:9",  # port fermé : le serveur ne répond pas
        **extra,
    )


def deposer(tmp_path: Path, rendezvous: list[dict[str, Any]], jour: str = JOUR) -> None:
    dossier = tmp_path / "journees"
    dossier.mkdir(parents=True, exist_ok=True)
    (dossier / f"{jour}.json").write_text(
        json.dumps(
            {
                "jour": jour,
                "lu_le": "2026-09-21T22:19:00",
                "agenda": "MOYAL Franck (Saint-Georges)",
                "rendezvous": rendezvous,
            }
        ),
        encoding="utf-8",
    )


RDV = {
    "heure": "09:30",
    "patient": "Chloé MOREAU",
    "prenom": "Chloé",
    "nom": "Moreau",
    "motif": "Contrôle périodique",
    "statut": "À venir",
    "dossier_cemedis": "",
}


def test_a_day_nobody_filed_is_reported_missing_not_invented(tmp_path: Path) -> None:
    journee = agenda.lire(reglages(tmp_path), JOUR)
    assert journee.source == "absent"
    assert journee.disponible is False
    assert journee.rendezvous == ()


def test_without_a_configured_connector_oris_does_not_go_looking(tmp_path: Path) -> None:
    deposer(tmp_path, [RDV])
    journee = agenda.lire(Settings(dental_lens_registre=tmp_path), JOUR)
    assert journee.source == "absent"


def test_the_day_file_is_read_when_the_dental_lens_server_is_down(tmp_path: Path) -> None:
    deposer(tmp_path, [RDV])
    journee = agenda.lire(reglages(tmp_path), JOUR)
    assert journee.source == "fichier"
    assert journee.agenda == "MOYAL Franck (Saint-Georges)"
    (rdv,) = journee.rendezvous
    assert (rdv.heure, rdv.prenom, rdv.nom) == ("09:30", "Chloé", "MOREAU")
    assert rdv.motif == "Contrôle périodique"
    # Sans le serveur, personne n'a interrogé SmileCloud : on ne prétend pas savoir.
    assert rdv.smilecloud == "inconnu"


def test_the_server_is_preferred_because_it_knows_the_smilecloud_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    deposer(tmp_path, [RDV])  # le fichier existe aussi : le serveur doit gagner

    def faux_get(url: str, **_: Any) -> httpx.Response:
        assert url.endswith("/api/journee")
        return httpx.Response(
            200,
            json={
                "jour": JOUR,
                "agenda": "MOYAL Franck (Saint-Georges)",
                "rendezvous": [{**RDV, "recherche": "trouve"}],
            },
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(httpx, "get", faux_get)
    journee = agenda.lire(reglages(tmp_path), JOUR)
    assert journee.source == "serveur"
    assert journee.rendezvous[0].smilecloud == "trouve"


def test_an_unknown_smilecloud_word_is_not_shown_as_is(tmp_path: Path) -> None:
    deposer(tmp_path, [{**RDV, "recherche": "quelque_chose_de_neuf"}])
    assert agenda.lire(reglages(tmp_path), JOUR).rendezvous[0].smilecloud == "inconnu"


def test_agenda_lines_that_are_not_patients_are_left_out(tmp_path: Path) -> None:
    """Une pause déjeuner n'est pas un rendez-vous : sans nom, la ligne est écartée."""
    deposer(tmp_path, [{"heure": "13:00", "motif": "Pause", "prenom": "", "nom": ""}, RDV])
    assert len(agenda.lire(reglages(tmp_path), JOUR).rendezvous) == 1


def test_a_damaged_day_file_does_not_break_the_screen(tmp_path: Path) -> None:
    dossier = tmp_path / "journees"
    dossier.mkdir(parents=True)
    (dossier / f"{JOUR}.json").write_text("{ceci n'est pas du json", encoding="utf-8")
    assert agenda.lire(reglages(tmp_path), JOUR).source == "absent"


def test_the_screen_matches_a_patient_oris_already_knows(api: Any, tmp_path: Path) -> None:
    """Doctolib écrit « MOREAU Chloé », Oris « Moreau Chloe » : c'est le même patient."""
    from oris_api.config import get_settings
    from oris_api.main import app

    connu = api.post("/patients", json={"first_name": "Chloe", "last_name": "Moreau"}).json()
    deposer(tmp_path, [RDV, {**RDV, "heure": "10:00", "prenom": "Karim", "nom": "Benali"}])
    app.dependency_overrides[get_settings] = lambda: reglages(tmp_path)
    try:
        reponse = api.get("/journee", params={"jour": JOUR})
    finally:
        app.dependency_overrides.pop(get_settings, None)

    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["disponible"] is True
    premier, second = corps["rendezvous"]
    assert premier["patient_id"] == connu["id"]
    assert second["patient_id"] is None  # à créer, mais pas par Oris tout seul
    # La lecture n'a ouvert aucun dossier.
    assert len(api.get("/patients").json()) == 1


def test_without_a_connector_the_screen_says_so_plainly(api: Any) -> None:
    corps = api.get("/journee", params={"jour": JOUR}).json()
    assert (corps["disponible"], corps["source"], corps["rendezvous"]) == (False, "absent", [])


def test_the_week_column_counts_the_files_still_missing(api: Any, tmp_path: Path) -> None:
    """Chaque jour de la colonne dit ce qu'il reste à faire, sans l'ouvrir."""
    from oris_api.config import get_settings
    from oris_api.main import app

    api.post("/patients", json={"first_name": "Chloe", "last_name": "Moreau"})
    deposer(tmp_path, [RDV, {**RDV, "prenom": "Karim", "nom": "Benali"}], jour="2026-09-22")
    deposer(tmp_path, [], jour="2026-09-23")

    app.dependency_overrides[get_settings] = lambda: reglages(tmp_path)
    try:
        semaine = api.get("/journee/semaine", params={"depuis": "2026-09-21", "jours": 3}).json()
    finally:
        app.dependency_overrides.pop(get_settings, None)

    lundi, mardi, mercredi = semaine
    assert (lundi["jour"], lundi["lu"], lundi["patients"]) == ("2026-09-21", False, 0)
    # Deux patients, dont un seul a déjà son dossier dans Oris.
    assert (mardi["lu"], mardi["patients"], mardi["a_creer"]) == (True, 2, 1)
    # Une journée lue et vide n'est pas une journée non lue : la nuance colore la colonne.
    assert (mercredi["lu"], mercredi["patients"]) == (True, 0)


def test_seven_silent_days_do_not_freeze_the_column(tmp_path: Path) -> None:
    """Le serveur muet n'est interrogé qu'une fois : sinon sept attentes s'enchaînent."""
    appels = 0

    def compter(*_: Any, **__: Any) -> httpx.Response:
        nonlocal appels
        appels += 1
        raise httpx.ConnectError("serveur éteint")

    semaine = []
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(httpx, "get", compter)
        semaine = agenda.lire_semaine(reglages(tmp_path), "2026-09-21", 7)

    assert appels == 1
    assert len(semaine) == 7


def test_a_day_the_server_answers_for_but_nobody_read_is_not_an_empty_day(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """« Jeudi n'a pas été relevé » et « jeudi n'a aucun patient » ne sont pas pareils."""

    def jamais_lue(url: str, **_: Any) -> httpx.Response:
        return httpx.Response(
            200,
            json={"jour": "2026-09-24", "agenda": "", "lu_le": None, "rendezvous": []},
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(httpx, "get", jamais_lue)
    journee = agenda.lire(reglages(tmp_path), "2026-09-24")
    assert journee.source == "serveur"
    assert journee.disponible is False
