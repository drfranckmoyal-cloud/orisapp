"""La civilité accorde les documents, et ne touche à rien d'autre.

Franck, le 27/10/2026, en relisant un compte rendu : « c'est un patient et pas une
patiente ». Oris ne savait pas : la fiche ne portait pas la civilité, et le rédacteur
devinait le genre d'après le prénom. Ces essais tiennent les trois promesses : la fiche
la garde, le rédacteur la reçoit, et sans elle il reçoit l'ordre de ne pas accorder.
"""

from __future__ import annotations

from typing import Any

from oris_api.documents.renderer import Style
from oris_api.domain.civilite import consigne
from oris_api.llm.redaction import message


def test_la_fiche_garde_la_civilite(api: Any) -> None:
    cree = api.post(
        "/patients",
        json={"first_name": "Jean", "last_name": "TEST", "civility": "monsieur"},
    )
    assert cree.status_code == 201, cree.text
    assert cree.json()["civility"] == "monsieur"

    patient_id = cree.json()["id"]
    assert api.get(f"/patients/{patient_id}").json()["civility"] == "monsieur"

    change = api.patch(f"/patients/{patient_id}", json={"civility": "madame"})
    assert change.status_code == 200, change.text
    assert change.json()["civility"] == "madame"

    # « On ne sait pas » est une réponse : elle doit pouvoir se dire après coup.
    efface = api.patch(f"/patients/{patient_id}", json={"civility": ""})
    assert efface.json()["civility"] == ""


def test_une_civilite_inventee_est_refusee(api: Any) -> None:
    refus = api.post(
        "/patients",
        json={"first_name": "Jean", "last_name": "TEST", "civility": "docteur"},
    )
    assert refus.status_code == 422


def test_un_patient_cree_sans_civilite_en_a_une_vide(api: Any) -> None:
    cree = api.post("/patients", json={"first_name": "Jean", "last_name": "TEST"})
    assert cree.status_code == 201, cree.text
    assert cree.json()["civility"] == ""


def test_le_redacteur_recoit_la_consigne_d_accord() -> None:
    masculin = message([], {}, Style(civilite="monsieur"))
    assert "accorde au masculin" in masculin

    feminin = message([], {}, Style(civilite="madame"))
    assert "accorde au féminin" in feminin


def test_sans_civilite_le_redacteur_a_l_ordre_de_ne_pas_accorder() -> None:
    """Le défaut ne doit pas être « masculin » : il doit être « n'accorde pas »."""
    sans = message([], {}, Style())
    assert "n'accorde pas au genre" in sans
    assert "Ne devine jamais le genre d'après le prénom" in sans
    assert "accorde au masculin" not in sans


def test_la_consigne_inconnue_retombe_sur_la_prudence() -> None:
    assert consigne("docteur") == consigne("")
