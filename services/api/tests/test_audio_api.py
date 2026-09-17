"""Capture audio via l'API : idempotence, contrôles, fin de session, purge, trous."""

from __future__ import annotations

import hashlib
import logging
from typing import Any

import pytest

from oris_api.domain.types import TranscriptionResult
from oris_api.main import app
from oris_api.providers import ProviderSet
from oris_api.services.audio import AUDIO_FORMAT
from oris_api.synthetic.corpus import default_corpus
from tests.conftest import clinical_object
from tests.test_logging import capture

SECOND = 32_000  # octets de PCM 16 kHz mono 16 bits


def pcm(seconds: float = 2.0, seed: int = 1) -> bytes:
    size = int(SECOND * seconds)
    return bytes((seed + i) % 256 for i in range(size - size % 2))


def new_encounter(api: Any, start: bool = True) -> str:
    patient = api.post("/patients", json={"first_name": "Test", "last_name": "Audio"}).json()
    eid: str = api.post("/encounters", json={"patient_id": patient["id"]}).json()["id"]
    if start:
        response = api.post(f"/encounters/{eid}/start", json={"patient_informed": True})
        assert response.status_code == 200, response.text
    return eid


def put_chunk(
    api: Any,
    eid: str,
    sequence: int,
    payload: bytes,
    timestamp_ms: int | None = None,
    checksum: str | None = None,
    content_type: str = AUDIO_FORMAT,
) -> Any:
    return api.put(
        f"/encounters/{eid}/audio/chunks/{sequence}",
        content=payload,
        headers={
            "Content-Type": content_type,
            "X-Chunk-Timestamp-Ms": str(sequence * 2000 if timestamp_ms is None else timestamp_ms),
            "X-Chunk-Checksum": checksum or hashlib.sha256(payload).hexdigest(),
        },
    )


def test_client_config_exposes_audio_contract(api: Any) -> None:
    config = api.get("/config/client").json()
    assert config["audio_format"] == AUDIO_FORMAT
    assert config["patient_information_mode"] == "confirm"
    assert (config["max_session_minutes"], config["warn_session_minutes"]) == (90, 80)


def test_start_requires_patient_information_when_configured(api: Any) -> None:
    eid = new_encounter(api, start=False)
    refused = api.post(f"/encounters/{eid}/start", json={})
    assert refused.status_code == 409
    assert refused.json()["code"] == "PATIENT_INFORMATION_REQUIRED"
    assert api.get(f"/encounters/{eid}").json()["status"] == "draft"


def test_start_without_information_when_mode_is_none(
    api: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from oris_api.config import Settings, get_settings

    app.dependency_overrides[get_settings] = lambda: Settings(patient_information_mode="none")
    eid = new_encounter(api, start=False)
    assert api.post(f"/encounters/{eid}/start").json()["status"] == "recording"
    del app.dependency_overrides[get_settings]


def test_chunks_are_idempotent_and_verified(api: Any) -> None:
    eid = new_encounter(api)
    chunk = pcm()
    first = put_chunk(api, eid, 0, chunk)
    assert (first.status_code, first.json()["status"]) == (201, "stored")
    again = put_chunk(api, eid, 0, chunk)
    assert (again.status_code, again.json()["status"]) == (200, "duplicate")

    conflict = put_chunk(api, eid, 0, pcm(seed=9))
    assert (conflict.status_code, conflict.json()["code"]) == (409, "CHUNK_CONFLICT")
    corrupted = put_chunk(api, eid, 1, pcm(), checksum="0" * 64)
    assert (corrupted.status_code, corrupted.json()["code"]) == (422, "CHECKSUM_MISMATCH")
    wrong_format = put_chunk(api, eid, 1, pcm(), content_type="audio/webm")
    assert wrong_format.json()["code"] == "UNSUPPORTED_AUDIO_FORMAT"
    too_large = put_chunk(api, eid, 1, pcm(seconds=9))
    assert too_large.json()["code"] == "CHUNK_TOO_LARGE"

    state = api.get(f"/encounters/{eid}/audio").json()
    assert state["received_count"] == 1
    assert (state["next_sequence"], state["next_timestamp_ms"]) == (1, 2000)
    assert state["received_duration_ms"] == 2000


def test_chunks_refused_outside_capture(api: Any) -> None:
    eid = new_encounter(api, start=False)
    response = put_chunk(api, eid, 0, pcm())
    assert response.status_code in {404, 409}


def test_pause_keeps_accepting_in_flight_chunks(api: Any) -> None:
    eid = new_encounter(api)
    put_chunk(api, eid, 0, pcm())
    assert api.post(f"/encounters/{eid}/pause").json()["status"] == "paused"
    assert put_chunk(api, eid, 1, pcm()).status_code == 201
    assert api.post(f"/encounters/{eid}/resume").json()["status"] == "recording"
    assert put_chunk(api, eid, 2, pcm()).status_code == 201


def test_finish_refuses_missing_chunks_then_accepts_declared_loss(api: Any) -> None:
    eid = new_encounter(api)
    for sequence in (0, 1, 3):
        put_chunk(api, eid, sequence, pcm())
    refused = api.post(f"/encounters/{eid}/finish", json={"final_sequence": 4})
    assert refused.status_code == 409
    assert refused.json()["code"] == "AUDIO_CHUNKS_MISSING"
    assert refused.json()["details"] == ["2", "4"]
    assert api.get(f"/encounters/{eid}").json()["status"] == "recording"

    # Le client renvoie le segment 2 ; le 4 est perdu pour de bon.
    put_chunk(api, eid, 2, pcm())
    finished = api.post(
        f"/encounters/{eid}/finish", json={"final_sequence": 4, "accept_gaps": True}
    )
    assert finished.status_code == 200
    audio = api.get(f"/encounters/{eid}/audio").json()
    assert audio["missing_sequences"] == [4]
    assert len(audio["gaps"]) == 1


def test_real_audio_without_stt_is_received_checked_and_purged(api: Any) -> None:
    eid = new_encounter(api)
    for sequence in range(3):
        put_chunk(api, eid, sequence, pcm())
    sink = app.state.audio_sink
    finished = api.post(
        f"/encounters/{eid}/finish", json={"final_sequence": 2, "client_recorded_ms": 6000}
    ).json()
    # M2 : aucun STT ne traite l'audio réel ; l'échec est visible, rien n'est inventé.
    assert finished["status"] == "transcription_failed"
    assert finished["processing_errors"][0]["rule"] == "NO_TRANSCRIPT"
    audio = api.get(f"/encounters/{eid}/audio").json()
    assert audio["purge_status"] == "purged" and audio["purged_at"]
    assert audio["received_count"] == 3  # métadonnées conservées pour l'audit
    session_ids = list(sink._data.keys())
    assert session_ids == []  # plus aucun son en mémoire


class EchoSpeechToText:
    """STT de test : un segment par seconde de son reçu."""

    def __init__(self, inner: Any) -> None:
        self.info = inner.info

    async def transcribe(self, chunks: Any, locale: str, glossary: Any) -> TranscriptionResult:
        case = default_corpus().get("ORIS-SYN-092")
        assert case is not None
        return TranscriptionResult(list(case.segments) if chunks else [])


@pytest.fixture
def echo_stt(api: Any) -> Any:
    original: ProviderSet = app.state.providers
    app.state.providers = ProviderSet(
        speech_to_text=EchoSpeechToText(original.speech_to_text),
        clinical_extraction=original.clinical_extraction,
        document_generation=original.document_generation,
        clinical_validation=original.clinical_validation,
    )
    yield api
    app.state.providers = original


def test_capture_gap_becomes_critical_warning_in_clinical_object(echo_stt: Any) -> None:
    api = echo_stt
    eid = new_encounter(api)
    put_chunk(api, eid, 0, pcm())
    put_chunk(api, eid, 1, pcm(), timestamp_ms=122_000)  # 2 minutes non captées
    finished = api.post(f"/encounters/{eid}/finish", json={"final_sequence": 1}).json()
    assert finished["status"] == "review"
    warnings = clinical_object(api, eid)["warnings"]
    assert [(w["code"], w["severity"]) for w in warnings] == [("AUDIO_GAP", "critical")]
    note = next(
        d
        for d in api.get(f"/encounters/{eid}/documents").json()
        if d["document_type"] == "consultation_note"
    )
    assert "ne peut pas être considéré comme exhaustif" in note["content"]


def test_reported_microphone_loss_becomes_critical_warning(echo_stt: Any) -> None:
    api = echo_stt
    eid = new_encounter(api)
    put_chunk(api, eid, 0, pcm())
    reported = api.post(
        f"/encounters/{eid}/audio/gaps", json={"reason": "microphone_lost", "duration_ms": 15_000}
    )
    assert reported.json()["reported_gap_reasons"] == ["microphone_lost"]
    put_chunk(api, eid, 1, pcm())
    api.post(f"/encounters/{eid}/finish", json={"final_sequence": 1})
    assert clinical_object(api, eid)["warnings"][0]["code"] == "AUDIO_GAP"


def test_complete_capture_has_no_warning(echo_stt: Any) -> None:
    api = echo_stt
    eid = new_encounter(api)
    for sequence in range(2):
        put_chunk(api, eid, sequence, pcm())
    api.post(f"/encounters/{eid}/finish", json={"final_sequence": 1})
    assert clinical_object(api, eid)["warnings"] == []


def test_finish_is_retry_safe(api: Any) -> None:
    eid = new_encounter(api)
    put_chunk(api, eid, 0, pcm())
    first = api.post(f"/encounters/{eid}/finish", json={"final_sequence": 0}).json()
    second = api.post(f"/encounters/{eid}/finish", json={"final_sequence": 0}).json()
    assert first["status"] == second["status"] == "transcription_failed"
    assert len(api.get("/encounters").json()) == 1


def test_audio_upload_logs_no_audio_or_checksum(api: Any) -> None:
    eid = new_encounter(api)
    chunk = pcm()
    checksum = hashlib.sha256(chunk).hexdigest()
    stream, handler = capture()
    try:
        put_chunk(api, eid, 0, chunk)
    finally:
        logging.getLogger().removeHandler(handler)
    output = stream.getvalue()
    assert "/encounters/{encounter_id}/audio/chunks/{sequence}" in output
    assert checksum not in output
