"""Le carnet d'adresses : confrères et structures.

Ce que ces tests tiennent :
- une structure ne porte ni civilité, ni prénom, ni spécialité — la lettre en dépend ;
- le filtre par spécialité retrouve aussi celles qui ne sont pas renseignées ;
- les spécialités du code ne se retirent pas, celles du cabinet si ;
- retirer une spécialité ne vide pas la fiche des correspondants qui la portaient.
"""

from __future__ import annotations

from typing import Any


def creer(api: Any, **champs: Any) -> dict[str, Any]:
    reponse = api.post("/correspondents", json={"last_name": "Durand", **champs})
    assert reponse.status_code == 201, reponse.text
    fiche: dict[str, Any] = reponse.json()
    return fiche


def test_a_practitioner_keeps_what_a_letter_needs(api: Any) -> None:
    fiche = creer(
        api,
        title="Dr",
        last_name="Lemaire",
        first_name="Claire",
        specialty="ODF",
        practice="Cabinet des Lilas",
        email="claire.lemaire@example.fr",
        phone="01 23 45 67 89",
        address="12 rue des Lilas\n75011 Paris",
        note="délai 3 mois",
    )
    assert fiche["kind"] == "practitioner"
    assert (fiche["title"], fiche["first_name"], fiche["specialty"]) == ("Dr", "Claire", "ODF")
    # L'adresse postale est la raison d'être de la fiche : elle ressort telle quelle.
    assert fiche["address"] == "12 rue des Lilas\n75011 Paris"


def test_an_organisation_has_neither_first_name_nor_title(api: Any) -> None:
    """Un CHU n'est pas un « Cher Confrère » : lui poser une civilité fausserait la lettre."""
    fiche = creer(
        api,
        kind="organisation",
        title="Dr",
        last_name="CHU de Rouen — service de chirurgie maxillo-faciale",
        first_name="Service",
        specialty="CMF",
    )
    assert (fiche["title"], fiche["first_name"], fiche["specialty"]) == ("", "", "")
    assert fiche["last_name"].startswith("CHU de Rouen")


def test_turning_a_practitioner_into_an_organisation_clears_what_no_longer_applies(
    api: Any,
) -> None:
    fiche = creer(api, title="Pr", first_name="Jean", specialty="CMF")
    change = api.patch(f"/correspondents/{fiche['id']}", json={"kind": "organisation"}).json()
    assert (change["title"], change["first_name"], change["specialty"]) == ("", "", "")


def test_an_unknown_title_is_refused(api: Any) -> None:
    reponse = api.post("/correspondents", json={"last_name": "Durand", "title": "Maître"})
    assert reponse.status_code == 422


def test_the_list_filters_by_specialty_including_the_unfilled_ones(api: Any) -> None:
    creer(api, last_name="Odf", specialty="ODF")
    creer(api, last_name="Cmf", specialty="CMF")
    creer(api, last_name="Sans")  # spécialité non renseignée

    odf = api.get("/correspondents", params={"specialty": "ODF"}).json()
    assert [c["last_name"] for c in odf] == ["Odf"]

    # Filtrer sur « non renseignée » sert à retrouver les fiches à compléter — une
    # structure n'a pas de spécialité par nature, pas par oubli, et n'y figure pas.
    creer(api, kind="organisation", last_name="CHU")
    vides = api.get("/correspondents", params={"specialty": ""}).json()
    assert [c["last_name"] for c in vides] == ["Sans"]

    assert len(api.get("/correspondents").json()) == 4


def test_the_list_searches_by_name_and_by_practice(api: Any) -> None:
    creer(api, last_name="Bernard", first_name="Alice", practice="Cabinet du Port")
    creer(api, last_name="Petit", first_name="Hugo", practice="Clinique Saint-Jean")

    assert len(api.get("/correspondents", params={"q": "bern"}).json()) == 1
    assert len(api.get("/correspondents", params={"q": "Port"}).json()) == 1
    assert len(api.get("/correspondents", params={"q": "zzz"}).json()) == 0


def test_the_cabinet_adds_its_own_specialties(api: Any) -> None:
    depart = api.get("/correspondents/specialties").json()
    assert depart == ["Omnipraticien", "ODF", "CMF"]

    apres = api.post("/correspondents/specialties", json={"label": "Parodontie"})
    assert apres.status_code == 201
    assert apres.json() == ["Omnipraticien", "ODF", "CMF", "Parodontie"]

    # Deux fois la même, à la casse près : refusé plutôt que doublé.
    assert api.post("/correspondents/specialties", json={"label": "parodontie"}).status_code == 409
    assert api.post("/correspondents/specialties", json={"label": "ODF"}).status_code == 409


def test_a_builtin_specialty_cannot_be_removed(api: Any) -> None:
    assert api.delete("/correspondents/specialties/ODF").status_code == 422


def test_removing_a_specialty_does_not_empty_the_records_that_carried_it(api: Any) -> None:
    """Le correspondant range le libellé, pas un renvoi : sa fiche ne bouge pas."""
    api.post("/correspondents/specialties", json={"label": "Parodontie"})
    fiche = creer(api, specialty="Parodontie")

    restantes = api.delete("/correspondents/specialties/Parodontie")
    assert restantes.status_code == 200
    assert "Parodontie" not in restantes.json()
    assert api.get(f"/correspondents/{fiche['id']}").json()["specialty"] == "Parodontie"


def test_a_correspondent_can_be_removed(api: Any) -> None:
    fiche = creer(api)
    assert api.delete(f"/correspondents/{fiche['id']}").status_code == 204
    assert api.get(f"/correspondents/{fiche['id']}").status_code == 404


def test_the_ones_put_forward_come_first(api: Any) -> None:
    """On adresse souvent aux trois ou quatre mêmes : ils remontent en tête."""
    creer(api, last_name="Zimmer")
    remonte = creer(api, last_name="Voisin")
    creer(api, last_name="Arnaud")

    assert [c["last_name"] for c in api.get("/correspondents").json()] == [
        "Arnaud",
        "Voisin",
        "Zimmer",
    ]
    api.patch(f"/correspondents/{remonte['id']}", json={"favorite": True})
    assert [c["last_name"] for c in api.get("/correspondents").json()] == [
        "Voisin",
        "Arnaud",
        "Zimmer",
    ]


def test_putting_forward_changes_nothing_else(api: Any) -> None:
    """L'étoile se met depuis la liste : elle ne doit toucher à aucun autre champ."""
    fiche = creer(api, title="Dr", first_name="Claire", specialty="ODF", email="c@example.fr")
    apres = api.patch(f"/correspondents/{fiche['id']}", json={"favorite": True}).json()
    assert apres["favorite"] is True
    assert {k: apres[k] for k in ("title", "first_name", "specialty", "email")} == {
        k: fiche[k] for k in ("title", "first_name", "specialty", "email")
    }


def test_a_second_address_and_number_can_be_kept(api: Any) -> None:
    """Le cabinet et le portable : les écraser l'un par l'autre obligeait à choisir."""
    fiche = creer(
        api,
        email="secretariat@example.fr",
        phone="01 23 45 67 89",
        secondary_email="claire.lemaire@example.fr",
        secondary_phone="06 11 22 33 44",
    )
    assert fiche["email"] == "secretariat@example.fr"
    assert fiche["secondary_email"] == "claire.lemaire@example.fr"
    assert fiche["secondary_phone"] == "06 11 22 33 44"


def test_the_second_contact_stays_empty_when_nobody_fills_it(api: Any) -> None:
    fiche = creer(api, email="unique@example.fr")
    assert (fiche["secondary_email"], fiche["secondary_phone"]) == ("", "")


def test_a_structure_keeps_its_second_number(api: Any) -> None:
    """Un service hospitalier a un standard et une ligne directe : les deux comptent."""
    fiche = creer(
        api,
        kind="organisation",
        last_name="CHU de Rouen",
        phone="02 32 88 89 90",
        secondary_phone="02 32 88 00 00",
    )
    assert fiche["secondary_phone"] == "02 32 88 00 00"
