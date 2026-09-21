"""Agenda du jour, déposé par l'extension Chrome (écran « Votre journée »).

Ce que ces tests tiennent :
- le dépôt range la journée et **n'écrit aucun patient en base** ;
- une lecture ratée de Doctolib n'efface pas la journée déjà déposée ;
- une journée jamais déposée est dite absente, jamais inventée ;
- le dépôt n'est ouvert qu'à cette machine ;
- un patient déjà connu d'Oris est reconnu malgré la casse et les accents.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from oris_api.config import Settings
from oris_api.services import agenda

JOUR = "2026-09-22"

#: Faux secret, seulement pour ce test.
JETON_DE_TEST = "secret-du-poste"

RDV = {
    "heure": "09:30",
    "patient": "Chloé MOREAU",
    "prenom": "Chloé",
    "nom": "Moreau",
    "motif": "Contrôle périodique",
    "statut": "À venir",
    "dossier_cemedis": "",
}


def reglages(tmp_path: Path) -> Settings:
    return Settings(journee_dir=tmp_path)


def livraison(rendezvous: list[dict[str, Any]], jour: str = JOUR, **extra: Any) -> dict[str, Any]:
    return {
        "jour": jour,
        "agenda": "MOYAL Franck (Saint-Georges)",
        "rendezvous": rendezvous,
        **extra,
    }


def test_a_delivered_day_comes_back_as_it_was_delivered(tmp_path: Path) -> None:
    reglage = reglages(tmp_path)
    depot = agenda.deposer(reglage, livraison([RDV]))
    assert (depot.jour, depot.rendezvous, depot.remplace) == (JOUR, 1, True)

    journee = agenda.lire(reglage, JOUR)
    assert journee.disponible is True
    assert journee.agenda == "MOYAL Franck (Saint-Georges)"
    assert journee.recu_le is not None
    (rdv,) = journee.rendezvous
    assert (rdv.heure, rdv.prenom, rdv.nom) == ("09:30", "Chloé", "MOREAU")
    assert rdv.motif == "Contrôle périodique"
    # L'extension ne dit rien de SmileCloud : on ne prétend pas savoir.
    assert rdv.smilecloud == "inconnu"


def test_a_day_nobody_delivered_is_reported_missing_not_invented(tmp_path: Path) -> None:
    journee = agenda.lire(reglages(tmp_path), JOUR)
    assert journee.disponible is False
    assert journee.rendezvous == ()


def test_a_later_delivery_replaces_the_previous_one(tmp_path: Path) -> None:
    """L'agenda bouge dans la journée : la dernière lecture fait foi."""
    reglage = reglages(tmp_path)
    agenda.deposer(reglage, livraison([RDV]))
    depot = agenda.deposer(reglage, livraison([RDV, {**RDV, "heure": "10:00", "nom": "Benali"}]))
    assert (depot.rendezvous, depot.remplace) == (2, True)
    assert len(agenda.lire(reglage, JOUR).rendezvous) == 2


def test_a_failed_reading_never_wipes_the_day_already_delivered(tmp_path: Path) -> None:
    """Doctolib lent ou tableau non compris : zéro ligne livrée, et la liste du matin
    est la seule que le praticien ait. Elle reste."""
    reglage = reglages(tmp_path)
    agenda.deposer(reglage, livraison([RDV]))

    depot = agenda.deposer(reglage, livraison([], diagnostic={"entetes": False, "lignes": 0}))
    assert depot.remplace is False
    assert depot.rendezvous == 1
    assert depot.raison is not None and "conservée" in depot.raison
    assert len(agenda.lire(reglage, JOUR).rendezvous) == 1


def test_an_empty_day_can_be_delivered_when_nothing_was_there_before(tmp_path: Path) -> None:
    """Un jour réellement vide doit pouvoir être déposé : sinon il reste « non relevé »."""
    reglage = reglages(tmp_path)
    depot = agenda.deposer(reglage, livraison([]))
    assert depot.remplace is True
    journee = agenda.lire(reglage, JOUR)
    assert (journee.disponible, journee.rendezvous) == (True, ())


def test_a_delivery_cannot_write_outside_its_folder(tmp_path: Path) -> None:
    """La date venue du dehors ne compose jamais un chemin telle quelle."""
    with pytest.raises(agenda.JourneeInvalide):
        agenda.deposer(reglages(tmp_path), livraison([RDV], jour="../../ailleurs"))
    assert list(tmp_path.rglob("*.json")) == []


def test_agenda_lines_that_are_not_patients_are_left_out(tmp_path: Path) -> None:
    """Une pause déjeuner n'est pas un rendez-vous : sans nom, la ligne est écartée."""
    reglage = reglages(tmp_path)
    agenda.deposer(reglage, livraison([{"heure": "13:00", "motif": "Pause"}, RDV]))
    assert len(agenda.lire(reglage, JOUR).rendezvous) == 1


def test_a_damaged_day_file_does_not_break_the_screen(tmp_path: Path) -> None:
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / f"{JOUR}.json").write_text("{ceci n'est pas du json", encoding="utf-8")
    assert agenda.lire(reglages(tmp_path), JOUR).disponible is False


def test_an_unknown_smilecloud_word_is_not_shown_as_is(tmp_path: Path) -> None:
    reglage = reglages(tmp_path)
    agenda.deposer(reglage, livraison([{**RDV, "recherche": "quelque_chose_de_neuf"}]))
    assert agenda.lire(reglage, JOUR).rendezvous[0].smilecloud == "inconnu"


# --- Le point d'entrée, tel que l'extension le voit --------------------------------


def depuis(adresse: str) -> Any:
    """Un client qui se présente avec l'adresse voulue.

    Le client de la fixture `api` s'annonce « testclient » : de quoi vérifier que le
    dépôt refuse ce qu'il ne reconnaît pas, mais pas de quoi jouer l'extension, qui
    appelle depuis cette machine. Pas de `with` : l'application est déjà démarrée par
    la fixture, la relancer réinitialiserait ses fournisseurs.
    """
    from starlette.testclient import TestClient

    from oris_api.main import app

    return TestClient(app, client=(adresse, 51000))


def deposer_par_api(api: Any, tmp_path: Path, corps: dict[str, Any], **kw: Any) -> Any:
    from oris_api.config import get_settings
    from oris_api.main import app

    app.dependency_overrides[get_settings] = lambda: reglages(tmp_path)
    try:
        return depuis("127.0.0.1").post("/journee/depot", json=corps, **kw)
    finally:
        app.dependency_overrides.pop(get_settings, None)


def test_the_deposit_stores_the_day_and_creates_no_patient(api: Any, tmp_path: Path) -> None:
    """Le cœur de la règle : déposer une journée ne fait entrer personne dans Oris."""
    reponse = deposer_par_api(api, tmp_path, livraison([RDV, {**RDV, "nom": "Benali"}]))
    assert reponse.status_code == 200
    assert reponse.json() == {"jour": JOUR, "rendezvous": 2, "remplace": True, "raison": None}
    assert api.get("/patients").json() == []


def test_the_deposit_is_closed_to_anything_but_this_machine(api: Any, tmp_path: Path) -> None:
    from oris_api.config import get_settings
    from oris_api.main import app

    app.dependency_overrides[get_settings] = lambda: reglages(tmp_path)
    try:
        reponse = depuis("203.0.113.7").post("/journee/depot", json=livraison([RDV]))
    finally:
        app.dependency_overrides.pop(get_settings, None)

    assert reponse.status_code == 403
    assert reponse.json()["code"] == "DEPOT_NON_LOCAL"
    assert list(tmp_path.rglob("*.json")) == []


def test_a_configured_token_is_required(api: Any, tmp_path: Path) -> None:
    from oris_api.config import get_settings
    from oris_api.main import app

    app.dependency_overrides[get_settings] = lambda: Settings(
        journee_dir=tmp_path, journee_depot_token=JETON_DE_TEST
    )
    extension = depuis("127.0.0.1")
    try:
        sans = extension.post("/journee/depot", json=livraison([RDV]))
        faux = extension.post(
            "/journee/depot", json=livraison([RDV]), headers={"Authorization": "Bearer autre"}
        )
        bon = extension.post(
            "/journee/depot",
            json=livraison([RDV]),
            headers={"Authorization": f"Bearer {JETON_DE_TEST}"},
        )
    finally:
        app.dependency_overrides.pop(get_settings, None)

    assert (sans.status_code, faux.status_code, bon.status_code) == (403, 403, 200)


def test_a_delivery_without_a_usable_date_is_refused(api: Any, tmp_path: Path) -> None:
    reponse = deposer_par_api(api, tmp_path, {"jour": "pas une date", "rendezvous": []})
    assert reponse.status_code == 422
    assert reponse.json()["code"] == "JOURNEE_INVALIDE"


def test_the_screen_matches_a_patient_oris_already_knows(api: Any, tmp_path: Path) -> None:
    """Doctolib écrit « MOREAU Chloé », Oris « Moreau Chloe » : c'est le même patient."""
    from oris_api.config import get_settings
    from oris_api.main import app

    connu = api.post("/patients", json={"first_name": "Chloe", "last_name": "Moreau"}).json()
    deposer_par_api(api, tmp_path, livraison([RDV, {**RDV, "prenom": "Karim", "nom": "Benali"}]))

    app.dependency_overrides[get_settings] = lambda: reglages(tmp_path)
    try:
        corps = api.get("/journee", params={"jour": JOUR}).json()
    finally:
        app.dependency_overrides.pop(get_settings, None)

    assert corps["disponible"] is True
    premier, second = corps["rendezvous"]
    assert premier["patient_id"] == connu["id"]
    assert second["patient_id"] is None  # à créer, mais pas par Oris tout seul
    assert len(api.get("/patients").json()) == 1


def test_the_week_column_counts_the_files_still_missing(api: Any, tmp_path: Path) -> None:
    """Chaque jour de la colonne dit ce qu'il reste à faire, sans l'ouvrir."""
    from oris_api.config import get_settings
    from oris_api.main import app

    api.post("/patients", json={"first_name": "Chloe", "last_name": "Moreau"})
    deposer_par_api(api, tmp_path, livraison([RDV, {**RDV, "prenom": "Karim", "nom": "Benali"}]))
    deposer_par_api(api, tmp_path, livraison([], jour="2026-09-23"))

    app.dependency_overrides[get_settings] = lambda: reglages(tmp_path)
    try:
        semaine = api.get("/journee/semaine", params={"depuis": "2026-09-21", "jours": 3}).json()
    finally:
        app.dependency_overrides.pop(get_settings, None)

    lundi, mardi, mercredi = semaine
    assert (lundi["jour"], lundi["lu"], lundi["patients"]) == ("2026-09-21", False, 0)
    # Deux patients, dont un seul a déjà son dossier dans Oris.
    assert (mardi["lu"], mardi["patients"], mardi["a_creer"]) == (True, 2, 1)
    # Une journée déposée et vide n'est pas une journée jamais relevée : la nuance
    # colore la colonne de gauche.
    assert (mercredi["lu"], mercredi["patients"]) == (True, 0)


# --- Demander une relecture ---------------------------------------------------------


def test_asking_for_a_day_puts_it_on_the_list_the_extension_reads(tmp_path: Path) -> None:
    reglage = reglages(tmp_path)
    quand = agenda.demander(reglage, JOUR)
    assert agenda.demandes(reglage) == {JOUR: quand}
    assert agenda.demande_pour(reglage, JOUR) == quand
    assert agenda.demande_pour(reglage, "2026-09-23") is None


def test_delivering_the_day_serves_the_request(tmp_path: Path) -> None:
    """La demande disparaît quand elle est satisfaite, pas à l'heure qu'il est."""
    reglage = reglages(tmp_path)
    agenda.demander(reglage, JOUR)
    agenda.deposer(reglage, livraison([RDV]))
    assert agenda.demandes(reglage) == {}


def test_a_failed_reading_leaves_the_request_standing(tmp_path: Path) -> None:
    """Une livraison refusée n'a rien servi : on attend toujours."""
    reglage = reglages(tmp_path)
    agenda.deposer(reglage, livraison([RDV]))
    agenda.demander(reglage, JOUR)
    depot = agenda.deposer(reglage, livraison([], diagnostic={"entetes": False}))
    assert depot.remplace is False
    assert JOUR in agenda.demandes(reglage)


def test_the_screen_and_the_extension_see_the_same_request(api: Any, tmp_path: Path) -> None:
    from oris_api.config import get_settings
    from oris_api.main import app

    app.dependency_overrides[get_settings] = lambda: reglages(tmp_path)
    try:
        demande = api.post("/journee/demande", json={"jour": JOUR})
        journee = api.get("/journee", params={"jour": JOUR}).json()
        attendues = depuis("127.0.0.1").get("/journee/demandes").json()
        dehors = depuis("203.0.113.7").get("/journee/demandes")
    finally:
        app.dependency_overrides.pop(get_settings, None)

    assert demande.status_code == 200
    assert demande.json()["jour"] == JOUR
    # L'écran sait qu'il attend ; l'extension sait quoi lire.
    assert journee["demande_le"] == demande.json()["demande_le"]
    assert attendues == [{"jour": JOUR, "demande_le": demande.json()["demande_le"]}]
    # Et personne d'autre ne sait ce que ce cabinet attend.
    assert dehors.status_code == 403


def test_asking_for_a_day_creates_no_patient_and_no_journee(api: Any, tmp_path: Path) -> None:
    from oris_api.config import get_settings
    from oris_api.main import app

    app.dependency_overrides[get_settings] = lambda: reglages(tmp_path)
    try:
        api.post("/journee/demande", json={"jour": JOUR})
        journee = api.get("/journee", params={"jour": JOUR}).json()
    finally:
        app.dependency_overrides.pop(get_settings, None)

    # Demander n'est pas recevoir : la journée reste non relevée.
    assert journee["disponible"] is False
    assert api.get("/patients").json() == []


def test_a_request_can_be_taken_back(api: Any, tmp_path: Path) -> None:
    """Une demande qui reste sans réponse ne doit pas coincer l'écran."""
    from oris_api.config import get_settings
    from oris_api.main import app

    app.dependency_overrides[get_settings] = lambda: reglages(tmp_path)
    try:
        api.post("/journee/demande", json={"jour": JOUR})
        retrait = api.delete("/journee/demande", params={"jour": JOUR})
        restantes = depuis("127.0.0.1").get("/journee/demandes").json()
    finally:
        app.dependency_overrides.pop(get_settings, None)

    assert retrait.status_code == 204
    assert restantes == []


def test_a_refused_delivery_leaves_a_trace_the_screen_can_show(tmp_path: Path) -> None:
    """Sans trace, l'extension réessayait, Oris refusait, et l'écran attendait en silence."""
    reglage = reglages(tmp_path)
    agenda.deposer(reglage, livraison([RDV]))
    agenda.deposer(reglage, livraison([], diagnostic={"entetes": False}))

    tentative = agenda.derniere_livraison(reglage, JOUR)
    assert tentative is not None
    assert tentative["remplace"] is False
    assert "conservée" in (tentative["raison"] or "")
    assert tentative["le"]


def test_a_served_delivery_leaves_its_trace_too(tmp_path: Path) -> None:
    reglage = reglages(tmp_path)
    agenda.deposer(reglage, livraison([RDV, {**RDV, "nom": "Benali"}]))
    tentative = agenda.derniere_livraison(reglage, JOUR)
    assert tentative is not None
    assert (tentative["remplace"], tentative["rendezvous"], tentative["raison"]) == (True, 2, None)


def test_a_request_nobody_served_within_the_hour_is_forgotten(tmp_path: Path) -> None:
    """Passé une heure, l'écran cesse d'attendre et propose de redemander."""
    from datetime import datetime, timedelta

    reglage = reglages(tmp_path)
    vieille = (datetime.now().astimezone() - timedelta(minutes=61)).isoformat(timespec="seconds")
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "demandes.json").write_text(json.dumps({JOUR: vieille}), encoding="utf-8")
    assert agenda.demandes(reglage) == {}
