"""Correction dictée par l'API : aperçu, confirmation, régénération, apprentissage."""

from __future__ import annotations

from typing import Any

from tests.conftest import clinical_object, documents_by_type, run_synthetic


def correct(api: Any, eid: str, command: str, **extra: Any) -> dict[str, Any]:
    body = {"command": command, **extra}
    response = api.post(f"/encounters/{eid}/corrections/text", json=body)
    assert response.status_code == 200, response.text
    return dict(response.json())


def test_a_correction_is_previewed_before_it_changes_anything(api: Any) -> None:
    eid = run_synthetic(api, "ORIS-SYN-092")["id"]
    preview = correct(api, eid, "remplace 16 par 17")
    assert preview["kind"] == "clinical"
    assert preview["impact"] == "high"
    assert preview["applied"] is False
    assert preview["operations"][0]["to_tooth"] == "17"
    # Le dossier n'a pas bougé.
    assert clinical_object(api, eid)["object_version"] == 1
    assert "16" in str(clinical_object(api, eid)["facts"])


def test_a_confirmed_correction_updates_the_record_and_rewrites_the_documents(api: Any) -> None:
    eid = run_synthetic(api, "ORIS-SYN-092")["id"]
    before = documents_by_type(api, eid)["consultation_note"]["content"]
    assert "16" in before

    applied = correct(api, eid, "remplace 16 par 17", apply=True, expected_object_version=1)
    assert applied["applied"] is True
    obj = clinical_object(api, eid)
    assert obj["object_version"] == 2
    assert all("16" not in fact["teeth"] for fact in obj["facts"])
    after = documents_by_type(api, eid)["consultation_note"]["content"]
    assert "17" in after and "16" not in after

    # La correction est retenue pour l'apprentissage.
    events = api.get(f"/encounters/{eid}/learning-events").json()
    assert any(event["event_type"] == "tooth_number_correction" for event in events)


def test_applying_without_the_version_is_refused(api: Any) -> None:
    eid = run_synthetic(api, "ORIS-SYN-092")["id"]
    response = api.post(
        f"/encounters/{eid}/corrections/text",
        json={"command": "remplace 16 par 17", "apply": True},
    )
    assert response.status_code == 409
    assert response.json()["code"] == "OBJECT_VERSION_REQUIRED"


def test_a_stale_version_is_refused(api: Any) -> None:
    eid = run_synthetic(api, "ORIS-SYN-092")["id"]
    correct(api, eid, "remplace 16 par 17", apply=True, expected_object_version=1)
    response = api.post(
        f"/encounters/{eid}/corrections/text",
        json={"command": "remplace 17 par 18", "apply": True, "expected_object_version": 1},
    )
    assert response.status_code == 409
    assert response.json()["code"] == "OBJECT_VERSION_CONFLICT"


def test_an_unclear_command_changes_nothing_and_explains(api: Any) -> None:
    eid = run_synthetic(api, "ORIS-SYN-092")["id"]
    answer = correct(api, eid, "mets une couronne sur la 14", apply=True, expected_object_version=1)
    assert answer["kind"] == "unclear"
    assert answer["applied"] is False
    assert clinical_object(api, eid)["object_version"] == 1


def test_a_style_request_is_remembered_but_never_touches_the_record(api: Any) -> None:
    eid = run_synthetic(api, "ORIS-SYN-092")["id"]
    answer = correct(
        api, eid, "fais le compte rendu plus court", apply=True, expected_object_version=1
    )
    assert answer["kind"] == "editorial" and answer["applied"] is True
    assert clinical_object(api, eid)["object_version"] == 1
    events = api.get(f"/encounters/{eid}/learning-events").json()
    assert any(event["event_type"] == "style_preference_detected" for event in events)


def test_a_correction_dictated_at_the_microphone_is_transcribed_then_interpreted(
    api: Any,
) -> None:
    """L'audio d'une correction est transcrit dans la requête, puis oublié."""
    from dataclasses import replace
    from typing import ClassVar

    from oris_api.contracts import TranscriptSegment
    from oris_api.domain.types import TranscriptionResult
    from oris_api.main import app
    from oris_api.providers.base import ProviderInfo

    class DictatedCorrection:
        info = ProviderInfo(name="test", version="0", capabilities=[])
        heard: ClassVar[list[int]] = []

        async def transcribe(self, chunks: Any, locale: str, glossary: Any) -> Any:
            DictatedCorrection.heard.append(len(chunks))
            return TranscriptionResult(
                [
                    TranscriptSegment(
                        segment_id="c1",
                        start_ms=0,
                        end_ms=1500,
                        speaker_role="practitioner",
                        text="Remplace 16 par 17.",
                        confidence=0.95,
                        is_final=True,
                    )
                ]
            )

    eid = run_synthetic(api, "ORIS-SYN-092")["id"]
    original = app.state.providers
    app.state.providers = replace(original, speech_to_text=DictatedCorrection())
    try:
        response = api.post(
            f"/encounters/{eid}/corrections/voice",
            content=b"\x00\x01" * 16000,
            headers={"content-type": "audio/pcm;rate=16000;channels=1;encoding=s16le"},
            params={"apply": True, "expected_object_version": 1},
        )
    finally:
        app.state.providers = original

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["kind"] == "clinical" and body["applied"] is True
    assert DictatedCorrection.heard == [1]
    obj = clinical_object(api, eid)
    assert obj["object_version"] == 2
    assert all("16" not in fact["teeth"] for fact in obj["facts"])
    # L'audio de la correction n'a pas été stocké : la consultation n'a pas de session
    # audio du tout (la consultation fictive n'en ouvre pas).
    assert api.get(f"/encounters/{eid}/audio").json().get("received_count", 0) == 0


def test_a_correction_audio_in_the_wrong_format_is_refused(api: Any) -> None:
    eid = run_synthetic(api, "ORIS-SYN-092")["id"]
    response = api.post(
        f"/encounters/{eid}/corrections/voice",
        content=b"\x00\x01",
        headers={"content-type": "audio/mpeg"},
    )
    assert response.status_code == 422
    assert response.json()["code"] == "UNSUPPORTED_AUDIO_FORMAT"
