"""Noter un envoi, supprimer une consultation.

Ce que ces tests tiennent :
- un envoi noté se voit dans la liste des consultations, sans doublon ;
- le nom du destinataire est recopié : supprimer le correspondant ne l'efface pas ;
- supprimer une consultation emporte ses documents, ses envois et ses corrections,
  jamais le patient ni ses pièces jointes ;
- on ne supprime pas une consultation pendant qu'Oris l'écoute.
"""

from __future__ import annotations

from typing import Any

from tests.conftest import documents_by_type


def consultation_traitee(api: Any) -> dict[str, Any]:
    patient = api.post("/patients", json={"first_name": "Test", "last_name": "Envoi"}).json()
    created = api.post(
        "/encounters", json={"patient_id": patient["id"], "synthetic_case_id": "ORIS-SYN-001"}
    ).json()
    api.post(f"/encounters/{created['id']}/start", json={"patient_informed": True})
    return dict(api.post(f"/encounters/{created['id']}/finish").json())


def test_a_noted_delivery_shows_in_the_list(api: Any) -> None:
    encounter = consultation_traitee(api)
    note = documents_by_type(api, encounter["id"])["consultation_note"]
    fiche = api.post("/correspondents", json={"title": "Dr", "last_name": "Martin"}).json()

    for _ in range(2):
        reponse = api.post(
            f"/documents/{note['id']}/deliveries",
            json={
                "recipient_kind": "correspondent",
                "correspondent_id": fiche["id"],
                "channel": "email",
            },
        )
        assert reponse.status_code == 201, reponse.text
    api.post(
        f"/documents/{note['id']}/deliveries", json={"recipient_kind": "patient", "channel": "hand"}
    )

    liste = api.get("/encounters").json()
    resume = next(d for d in liste[0]["documents"] if d["id"] == note["id"])
    assert resume["sent_to"] == ["Dr Martin", "le patient"]
    assert len(api.get(f"/encounters/{encounter['id']}/deliveries").json()) == 3


def test_the_recipient_name_survives_the_correspondent(api: Any) -> None:
    encounter = consultation_traitee(api)
    note = documents_by_type(api, encounter["id"])["consultation_note"]
    fiche = api.post("/correspondents", json={"title": "Dr", "last_name": "Martin"}).json()
    api.post(
        f"/documents/{note['id']}/deliveries",
        json={
            "recipient_kind": "correspondent",
            "correspondent_id": fiche["id"],
            "channel": "mail",
        },
    )
    api.delete(f"/correspondents/{fiche['id']}")

    envois = api.get(f"/encounters/{encounter['id']}/deliveries").json()
    assert envois[0]["recipient_label"] == "Dr Martin"
    assert envois[0]["correspondent_id"] is None


def test_another_recipient_needs_a_name_and_can_be_removed(api: Any) -> None:
    encounter = consultation_traitee(api)
    note = documents_by_type(api, encounter["id"])["consultation_note"]
    sans_nom = api.post(
        f"/documents/{note['id']}/deliveries", json={"recipient_kind": "other", "channel": "mail"}
    )
    assert sans_nom.status_code == 422

    envoi = api.post(
        f"/documents/{note['id']}/deliveries",
        json={"recipient_kind": "other", "recipient_label": "Mutuelle", "channel": "mail"},
    ).json()
    assert api.delete(f"/deliveries/{envoi['id']}").status_code == 204
    assert api.get(f"/encounters/{encounter['id']}/deliveries").json() == []


def test_deleting_a_consultation_takes_its_documents_not_the_patient(api: Any) -> None:
    encounter = consultation_traitee(api)
    note = documents_by_type(api, encounter["id"])["consultation_note"]
    api.post(
        f"/documents/{note['id']}/deliveries", json={"recipient_kind": "patient", "channel": "hand"}
    )

    assert api.delete(f"/encounters/{encounter['id']}").status_code == 204

    assert api.get(f"/encounters/{encounter['id']}").status_code == 404
    assert api.get(f"/documents/{note['id']}").status_code == 404
    assert api.get(f"/patients/{encounter['patient']['id']}").status_code == 200
    assert api.get("/encounters").json() == []


def test_a_consultation_being_recorded_cannot_be_deleted(api: Any) -> None:
    patient = api.post("/patients", json={"first_name": "Test", "last_name": "Ecoute"}).json()
    created = api.post("/encounters", json={"patient_id": patient["id"]}).json()
    api.post(f"/encounters/{created['id']}/start", json={"patient_informed": True})

    refus = api.delete(f"/encounters/{created['id']}")
    assert refus.status_code == 409
    assert refus.json()["code"] == "ENCOUNTER_IN_PROGRESS"


def test_a_draft_that_never_started_can_be_deleted(api: Any) -> None:
    patient = api.post("/patients", json={"first_name": "Test", "last_name": "Brouillon"}).json()
    created = api.post("/encounters", json={"patient_id": patient["id"]}).json()
    assert api.delete(f"/encounters/{created['id']}").status_code == 204


def test_the_visit_kind_chosen_before_listening_is_kept(api: Any) -> None:
    patient = api.post("/patients", json={"first_name": "Test", "last_name": "Acte"}).json()
    created = api.post("/encounters", json={"patient_id": patient["id"]}).json()
    assert created["visit_kind"] == "consultation"

    started = api.post(
        f"/encounters/{created['id']}/start",
        json={"patient_informed": True, "visit_kind": "procedure"},
    ).json()
    assert started["visit_kind"] == "procedure"
    assert api.get(f"/encounters/{created['id']}").json()["visit_kind"] == "procedure"


def test_an_unknown_visit_kind_is_refused(api: Any) -> None:
    patient = api.post("/patients", json={"first_name": "Test", "last_name": "Acte"}).json()
    created = api.post("/encounters", json={"patient_id": patient["id"]}).json()
    reponse = api.post(
        f"/encounters/{created['id']}/start",
        json={"patient_informed": True, "visit_kind": "suivi"},
    )
    assert reponse.status_code == 422


def test_a_referral_letter_is_written_only_when_asked(api: Any) -> None:
    encounter = consultation_traitee(api)
    assert "referral_letter" not in documents_by_type(api, encounter["id"])

    cree = api.post(f"/encounters/{encounter['id']}/documents/referral-letter")
    assert cree.status_code == 200, cree.text
    lettre = documents_by_type(api, encounter["id"])["referral_letter"]
    pdf = api.get(f"/documents/{lettre['id']}/export", params={"format": "pdf"})
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")

    # Une fois demandé, il suit les corrections comme les autres documents.
    api.post(f"/encounters/{encounter['id']}/documents/generate")
    assert "referral_letter" in documents_by_type(api, encounter["id"])
