"""Mode ombre : Oris écrit en parallèle, aucune de ses sorties n'entre dans un dossier."""

from __future__ import annotations

from typing import Any

from tests.conftest import documents_by_type


def shadow_encounter(api: Any, case_id: str = "ORIS-SYN-092") -> dict[str, Any]:
    patient = api.post("/patients", json={"first_name": "Test", "last_name": "Ombre"}).json()
    created = api.post(
        "/encounters",
        json={"patient_id": patient["id"], "synthetic_case_id": case_id, "shadow": True},
    ).json()
    api.post(f"/encounters/{created['id']}/start", json={"patient_informed": True})
    return dict(api.post(f"/encounters/{created['id']}/finish").json())


def test_a_shadow_consultation_is_processed_like_the_others(api: Any) -> None:
    encounter = shadow_encounter(api)
    assert encounter["mode"] == "shadow"
    assert encounter["status"] == "review"
    # Oris a bien travaillé : c'est l'intérêt du mode ombre, mesurer en conditions réelles.
    assert "consultation_note" in documents_by_type(api, encounter["id"])


def test_a_shadow_document_can_never_be_validated(api: Any) -> None:
    encounter = shadow_encounter(api)
    note = documents_by_type(api, encounter["id"])["consultation_note"]
    refused = api.post(f"/documents/{note['id']}/validate", json={"acknowledged_warning_codes": []})
    assert refused.status_code == 409
    assert refused.json()["code"] == "SHADOW_ENCOUNTER"


def test_a_shadow_document_can_never_be_exported(api: Any) -> None:
    encounter = shadow_encounter(api)
    note = documents_by_type(api, encounter["id"])["consultation_note"]
    for fmt in ("pdf", "text", "structured"):
        refused = api.get(f"/documents/{note['id']}/export", params={"format": fmt})
        assert refused.status_code == 409, fmt
        assert refused.json()["code"] == "SHADOW_ENCOUNTER"


def test_an_ordinary_consultation_is_not_affected(api: Any) -> None:
    from tests.conftest import run_synthetic

    eid = run_synthetic(api, "ORIS-SYN-092")["id"]
    assert api.get(f"/encounters/{eid}").json()["mode"] == "consultation"
    note = documents_by_type(api, eid)["consultation_note"]
    assert (
        api.post(
            f"/documents/{note['id']}/validate", json={"acknowledged_warning_codes": []}
        ).status_code
        == 200
    )


def test_the_shadow_mode_is_written_in_the_audit_trail(api: Any) -> None:
    encounter = shadow_encounter(api)
    events = api.get("/audit", params={"encounter_id": encounter["id"]}).json()
    created = [event for event in events if event["action"] == "encounter.created"]
    assert created and created[0]["details"]["mode"] == "shadow"
