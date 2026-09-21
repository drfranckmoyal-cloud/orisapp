"""Rattacher un patient à ses correspondants.

Ce que ces tests tiennent :
- le rôle est porté par le lien, pas par le correspondant ;
- refaire le geste corrige le rôle au lieu de doubler la ligne ;
- un correspondant supprimé emporte ses liens, jamais les patients.
"""

from __future__ import annotations

from typing import Any


def patient(api: Any, nom: str = "Rattache") -> str:
    return str(api.post("/patients", json={"first_name": "Jean", "last_name": nom}).json()["id"])


def correspondant(api: Any, nom: str = "Lemaire", **champs: Any) -> str:
    return str(api.post("/correspondents", json={"last_name": nom, **champs}).json()["id"])


def test_the_link_says_which_way_the_patient_went(api: Any) -> None:
    """« Qui me l'a adressé » et « à qui je l'adresse » ne sont pas la même chose."""
    p = patient(api)
    envoyeur = correspondant(api, "Bernard")
    receveur = correspondant(api, "Voisin")

    api.post(
        f"/patients/{p}/correspondents", json={"correspondent_id": envoyeur, "role": "referred_by"}
    )
    liens = api.post(
        f"/patients/{p}/correspondents", json={"correspondent_id": receveur, "role": "referred_to"}
    ).json()

    assert [(lien["correspondent"]["last_name"], lien["role"]) for lien in liens] == [
        ("Bernard", "referred_by"),
        ("Voisin", "referred_to"),
    ]


def test_the_same_correspondent_can_send_one_patient_and_receive_another(api: Any) -> None:
    """Le rôle tient au lien : un confrère n'est pas « un adressant » une fois pour toutes."""
    fiche = correspondant(api, "Bernard")
    envoye = patient(api, "Envoye")
    recu = patient(api, "Recu")

    api.post(
        f"/patients/{envoye}/correspondents",
        json={"correspondent_id": fiche, "role": "referred_by"},
    )
    api.post(
        f"/patients/{recu}/correspondents", json={"correspondent_id": fiche, "role": "referred_to"}
    )

    assert api.get(f"/patients/{envoye}/correspondents").json()[0]["role"] == "referred_by"
    assert api.get(f"/patients/{recu}/correspondents").json()[0]["role"] == "referred_to"


def test_attaching_twice_corrects_the_role_instead_of_doubling_the_line(api: Any) -> None:
    p = patient(api)
    fiche = correspondant(api)

    api.post(
        f"/patients/{p}/correspondents", json={"correspondent_id": fiche, "role": "referred_by"}
    )
    liens = api.post(
        f"/patients/{p}/correspondents", json={"correspondent_id": fiche, "role": "also_follows"}
    ).json()

    assert len(liens) == 1
    assert liens[0]["role"] == "also_follows"


def test_an_unknown_role_is_refused(api: Any) -> None:
    p = patient(api)
    fiche = correspondant(api)
    reponse = api.post(
        f"/patients/{p}/correspondents", json={"correspondent_id": fiche, "role": "ami"}
    )
    assert reponse.status_code == 422


def test_a_correspondent_of_another_patient_is_not_visible_here(api: Any) -> None:
    autre = patient(api, "Autre")
    p = patient(api)
    api.post(
        f"/patients/{autre}/correspondents",
        json={"correspondent_id": correspondant(api), "role": "referred_by"},
    )
    assert api.get(f"/patients/{p}/correspondents").json() == []


def test_detaching_leaves_the_correspondent_in_the_address_book(api: Any) -> None:
    """Retirer un confrère d'une fiche patient ne le raye pas du carnet."""
    p = patient(api)
    fiche = correspondant(api)
    api.post(
        f"/patients/{p}/correspondents", json={"correspondent_id": fiche, "role": "referred_by"}
    )

    assert api.delete(f"/patients/{p}/correspondents/{fiche}").status_code == 204
    assert api.get(f"/patients/{p}/correspondents").json() == []
    assert api.get(f"/correspondents/{fiche}").status_code == 200


def test_deleting_a_correspondent_takes_its_links_and_leaves_the_patients(api: Any) -> None:
    p = patient(api)
    fiche = correspondant(api)
    api.post(
        f"/patients/{p}/correspondents", json={"correspondent_id": fiche, "role": "referred_by"}
    )

    assert api.delete(f"/correspondents/{fiche}").status_code == 204
    assert api.get(f"/patients/{p}/correspondents").json() == []
    # Le patient, lui, ne bouge pas.
    assert api.get(f"/patients/{p}").status_code == 200
