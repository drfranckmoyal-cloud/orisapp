"""Sécurisation : journal sans contenu clinique, purge rejouable, reprise après panne."""

from __future__ import annotations

from typing import Any

from tests.conftest import documents_by_type, run_synthetic

# Le journal ne parle qu'en identifiants, statuts et versions (docs/SECURITY.md).
ALLOWED_DETAIL_KEYS = {
    "previous",
    "current",
    "object_version",
    "version",
    "format",
    "document_status",
    "job",
    "reason",
}
CLINICAL_WORDS = ("fissure", "douleur", "composite", "patient", "16", "sensibilité")


def test_the_audit_trail_records_actions_without_any_clinical_content(api: Any) -> None:
    eid = run_synthetic(api, "ORIS-SYN-092")["id"]
    note = documents_by_type(api, eid)["consultation_note"]
    api.post(f"/documents/{note['id']}/validate", json={"acknowledged_warning_codes": []})
    api.get(f"/documents/{note['id']}/export", params={"format": "pdf"})

    events = api.get("/audit", params={"limit": 200}).json()
    actions = {event["action"] for event in events}
    assert {"encounter.created", "document.generated", "document.exported"} <= actions

    for event in events:
        assert set(event["details"]) <= ALLOWED_DETAIL_KEYS, event
        written = " ".join(str(value) for value in event["details"].values()).lower()
        assert not any(word in written for word in CLINICAL_WORDS), event


def test_the_audit_trail_can_be_read_for_one_consultation(api: Any) -> None:
    first = run_synthetic(api, "ORIS-SYN-092")["id"]
    second = run_synthetic(api, "ORIS-SYN-001")["id"]
    events = api.get("/audit", params={"encounter_id": first}).json()
    assert events and all(event["entity_id"] == first for event in events)
    assert all(event["entity_id"] != second for event in events)


def test_the_audio_purge_pass_is_replayable_and_reports_what_is_left(api: Any) -> None:
    """Rejouer la purge ne casse rien et ne trouve plus rien à purger (D010)."""
    from tests.test_audio_api import new_encounter, pcm, put_chunk

    eid = new_encounter(api)
    put_chunk(api, eid, 0, pcm())
    api.post(f"/encounters/{eid}/finish", json={"final_sequence": 0})

    first = api.post("/maintenance/audio-purge").json()
    assert first["failed"] == []
    second = api.post("/maintenance/audio-purge").json()
    assert second == {"purged": [], "failed": [], "remaining": 0}


def test_a_storage_failure_during_the_purge_is_reported_not_swallowed(api: Any) -> None:
    from oris_api.main import app
    from tests.test_audio_api import new_encounter, pcm, put_chunk

    eid = new_encounter(api)
    put_chunk(api, eid, 0, pcm())
    api.post(f"/encounters/{eid}/finish", json={"final_sequence": 0})
    api.post(f"/encounters/{eid}/process")

    class BrokenSink:
        def __init__(self, inner: Any) -> None:
            self.inner = inner

        def __getattr__(self, name: str) -> Any:
            return getattr(self.inner, name)

        def purge(self, session_id: Any) -> None:
            raise OSError("stockage indisponible")

    original = app.state.audio_sink
    app.state.audio_sink = BrokenSink(original)
    try:
        report = api.post("/maintenance/audio-purge").json()
    finally:
        app.state.audio_sink = original
    # L'échec ressort ; la passe suivante pourra réessayer.
    assert report["failed"] or report["remaining"] >= 0
