"""Envoyer un document par courriel.

Ce que ces tests tiennent :
- le nom du PDF dit le type, le patient et la date ;
- le correspondant qui a adressé le patient est coché d'office ;
- un courriel par destinataire, le PDF joint, et chaque envoi noté « Envoyé à » ;
- sans boîte d'envoi configurée, rien ne part et l'écran sait pourquoi.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

from oris_api.services.courriel import MessagerieMemoire
from tests.conftest import documents_by_type
from tests.test_deliveries_and_deletion import consultation_traitee


@pytest.fixture
def boite(api: Any) -> Iterator[MessagerieMemoire]:
    from oris_api.main import app

    memoire = MessagerieMemoire()
    avant = app.state.messagerie
    app.state.messagerie = memoire
    api.patch("/me/cabinet", json={"sending_email": "praticien@cabinet.test"})
    yield memoire
    app.state.messagerie = avant


def preparer_patient(api: Any) -> tuple[dict[str, Any], str, str]:
    encounter = consultation_traitee(api)
    patient_id = encounter["patient"]["id"]
    api.patch(f"/patients/{patient_id}", json={"email": "patient@exemple.test"})
    adressant = api.post(
        "/correspondents",
        json={
            "title": "Dr",
            "first_name": "Claire",
            "last_name": "Martin",
            "email": "c.martin@exemple.test",
        },
    ).json()
    api.post(
        f"/patients/{patient_id}/correspondents",
        json={"correspondent_id": adressant["id"], "role": "referred_by"},
    )
    note = documents_by_type(api, encounter["id"])["consultation_note"]
    return encounter, note["id"], adressant["id"]


def test_the_pdf_is_named_after_its_type_patient_and_date(api: Any) -> None:
    encounter = consultation_traitee(api)
    note = documents_by_type(api, encounter["id"])["consultation_note"]
    reponse = api.get(f"/documents/{note['id']}/export", params={"format": "pdf"})
    disposition = reponse.headers["content-disposition"]
    assert 'filename="Compte-rendu-consultation_ENVOI-Test_' in disposition
    assert disposition.endswith('.pdf"')


def test_the_referring_colleague_is_checked_by_default(api: Any, boite: MessagerieMemoire) -> None:
    _, note_id, adressant = preparer_patient(api)
    prepare = api.get(f"/documents/{note_id}/envoi").json()
    assert prepare["configure"] is True
    coches = {c["cle"]: c["coche"] for c in prepare["candidats"]}
    assert coches == {"patient": False, adressant: True}
    assert prepare["objet"].startswith("Compte rendu de consultation — Test ENVOI")


def test_one_message_per_recipient_with_the_pdf_and_each_send_is_noted(
    api: Any, boite: MessagerieMemoire
) -> None:
    encounter, note_id, adressant = preparer_patient(api)
    resultats = api.post(
        f"/documents/{note_id}/envoi",
        json={
            "destinataires": [adressant, "patient"],
            "adresses": ["mutuelle@exemple.test"],
            "objet": "Compte rendu",
            "message": "Cher confrère,",
        },
    )
    assert resultats.status_code == 200, resultats.text
    assert all(r["envoye"] for r in resultats.json())
    assert [m["To"] for m in boite.envoyes] == [
        "c.martin@exemple.test",
        "patient@exemple.test",
        "mutuelle@exemple.test",
    ]
    piece = next(boite.envoyes[0].iter_attachments())
    assert piece.get_filename().startswith("Compte-rendu-consultation_ENVOI-Test_")
    assert piece.get_content().startswith(b"%PDF")
    resume = api.get(f"/encounters/{encounter['id']}").json()["documents"]
    envoye_a = next(d for d in resume if d["id"] == note_id)["sent_to"]
    assert envoye_a == ["Dr Martin", "le patient", "mutuelle@exemple.test"]


def test_nothing_leaves_without_a_configured_mailbox(api: Any) -> None:
    _, note_id, adressant = preparer_patient(api)
    api.patch("/me/cabinet", json={"sending_email": "praticien@cabinet.test"})
    assert api.get(f"/documents/{note_id}/envoi").json()["raison"] == "SMTP_NOT_CONFIGURED"
    refus = api.post(
        f"/documents/{note_id}/envoi",
        json={"destinataires": [adressant], "objet": "x", "message": "y"},
    )
    assert refus.status_code == 409
    assert refus.json()["code"] == "SMTP_NOT_CONFIGURED"


def test_a_recipient_outside_the_patient_file_must_be_typed(
    api: Any, boite: MessagerieMemoire
) -> None:
    _, note_id, _ = preparer_patient(api)
    refus = api.post(
        f"/documents/{note_id}/envoi",
        json={"destinataires": ["inconnu"], "objet": "x", "message": "y"},
    )
    assert refus.status_code == 422
    assert boite.envoyes == []


def test_the_website_may_read_the_pdf_name(api: Any) -> None:
    encounter = consultation_traitee(api)
    note = documents_by_type(api, encounter["id"])["consultation_note"]
    reponse = api.get(
        f"/documents/{note['id']}/export",
        params={"format": "pdf"},
        headers={"Origin": "http://localhost:3000"},
    )
    assert "content-disposition" in reponse.headers["access-control-expose-headers"].lower()


def test_an_exported_document_counts_as_validated_for_the_consultation(api: Any) -> None:
    encounter = consultation_traitee(api)
    for document in documents_by_type(api, encounter["id"]).values():
        api.post(f"/documents/{document['id']}/validate", json={"acknowledged_warning_codes": []})
    note = documents_by_type(api, encounter["id"])["consultation_note"]
    api.get(f"/documents/{note['id']}/export", params={"format": "pdf"})
    valide = api.post(f"/encounters/{encounter['id']}/validate")
    assert valide.status_code == 200, valide.text


def test_one_validated_document_validates_the_consultation_the_others_stay_independent(
    api: Any,
) -> None:
    encounter = consultation_traitee(api)
    docs = documents_by_type(api, encounter["id"])
    assert len(docs) >= 2
    note = docs["consultation_note"]
    api.post(f"/documents/{note['id']}/validate", json={"acknowledged_warning_codes": []})
    assert api.get(f"/encounters/{encounter['id']}").json()["status"] == "validated"
    # Le plan reste un brouillon, qu'on valide plus tard, sans rien débloquer.
    plan = documents_by_type(api, encounter["id"])["treatment_plan_text"]
    assert plan["status"] in {"draft_ai", "needs_review"}
    valide = api.post(f"/documents/{plan['id']}/validate", json={"acknowledged_warning_codes": []})
    assert valide.status_code == 200, valide.text


def test_any_document_can_be_removed(api: Any) -> None:
    encounter = consultation_traitee(api)
    api.post(f"/encounters/{encounter['id']}/documents/referral-letter")
    docs = documents_by_type(api, encounter["id"])
    assert api.delete(f"/documents/{docs['referral_letter']['id']}").status_code == 204
    assert "referral_letter" not in documents_by_type(api, encounter["id"])
    # Il ne revient pas tout seul à la régénération suivante.
    api.post(f"/encounters/{encounter['id']}/documents/generate")
    assert "referral_letter" not in documents_by_type(api, encounter["id"])
    # Le compte rendu et le plan aussi (choix du 21/09/2026) ; le dossier clinique reste.
    assert api.delete(f"/documents/{docs['consultation_note']['id']}").status_code == 204
    assert api.delete(f"/documents/{docs['treatment_plan_text']['id']}").status_code == 204
    restants = documents_by_type(api, encounter["id"])
    assert "consultation_note" not in restants and "treatment_plan_text" not in restants
    assert api.get(f"/encounters/{encounter['id']}/clinical-object").status_code == 200


def test_asking_for_a_letter_leaves_the_validated_report_alone(api: Any) -> None:
    encounter = consultation_traitee(api)
    note = documents_by_type(api, encounter["id"])["consultation_note"]
    api.post(f"/documents/{note['id']}/validate", json={"acknowledged_warning_codes": []})
    api.post(f"/encounters/{encounter['id']}/documents/referral-letter")
    apres = documents_by_type(api, encounter["id"])
    assert apres["consultation_note"]["status"] == "validated"
    assert apres["consultation_note"]["version"] == note["version"]
    assert api.get(f"/encounters/{encounter['id']}").json()["status"] == "validated"


def test_a_single_document_can_be_redrafted_without_touching_the_others(api: Any) -> None:
    encounter = consultation_traitee(api)
    docs = documents_by_type(api, encounter["id"])
    api.post(
        f"/documents/{docs['treatment_plan_text']['id']}/validate",
        json={"acknowledged_warning_codes": []},
    )
    note = docs["consultation_note"]
    reponse = api.post(f"/documents/{note['id']}/rediger")
    assert reponse.status_code == 200
    apres = documents_by_type(api, encounter["id"])
    assert apres["consultation_note"]["version"] == note["version"] + 1
    assert apres["treatment_plan_text"]["status"] == "validated"
