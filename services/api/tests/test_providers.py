"""Fournisseurs factices : configuration, contrat, absence d'invention."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from oris_api.config import Settings
from oris_api.contracts import ClinicalEncounter, ClinicalFact, TranscriptSegment
from oris_api.providers import (
    ClinicalExtractionProvider,
    ClinicalValidationProvider,
    DocumentGenerationProvider,
    GeneratedDocument,
    SpeechToTextProvider,
    build_providers,
)
from oris_api.providers.mock import (
    MockClinicalExtractionProvider,
    MockClinicalValidationProvider,
    MockDocumentGenerationProvider,
    MockSpeechToTextProvider,
)


def encounter_from_case(case: dict[str, Any]) -> ClinicalEncounter:
    return ClinicalEncounter.model_validate(
        {
            "encounter_id": "enc-test",
            "patient_id": "pat-test",
            "practitioner_id": "usr-test",
            "started_at": "2026-09-16T09:00:00Z",
            "ended_at": None,
            "status": "review",
            "object_version": 1,
            "facts": case["expected"]["facts"],
            "treatment_plan": case["expected"]["treatment_plan"],
            "procedures": case["expected"]["procedures"],
            "warnings": [],
        }
    )


def test_default_settings_build_mock_providers_satisfying_interfaces() -> None:
    providers = build_providers(Settings())
    assert isinstance(providers.speech_to_text, SpeechToTextProvider)
    assert isinstance(providers.clinical_extraction, ClinicalExtractionProvider)
    assert isinstance(providers.document_generation, DocumentGenerationProvider)
    assert isinstance(providers.clinical_validation, ClinicalValidationProvider)


@pytest.mark.parametrize(
    "variable",
    ["STT_PROVIDER", "CLINICAL_EXTRACTION_PROVIDER", "DOCUMENT_GENERATION_PROVIDER"],
)
def test_real_providers_are_refused(variable: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(variable, "some_vendor")
    with pytest.raises(ValueError):
        Settings()


def test_mock_stt_returns_scripted_segments(corpus_cases: list[dict[str, Any]]) -> None:
    segments = [TranscriptSegment.model_validate(s) for s in corpus_cases[0]["transcript_segments"]]
    provider = MockSpeechToTextProvider(segments)
    assert asyncio.run(provider.transcribe([], "fr-FR", [])) == segments


def test_mock_extraction_without_script_invents_nothing(
    corpus_cases: list[dict[str, Any]],
) -> None:
    segments = [TranscriptSegment.model_validate(s) for s in corpus_cases[0]["transcript_segments"]]
    assert asyncio.run(MockClinicalExtractionProvider().extract(segments, [])) == []


def test_mock_extraction_drops_audio_facts_without_evidence(
    corpus_cases: list[dict[str, Any]],
) -> None:
    case = corpus_cases[90]
    fact = ClinicalFact.model_validate(
        dict(case["expected"]["facts"][0], source_type="audio", evidence_segment_ids=["absent"])
    )
    segments = [TranscriptSegment.model_validate(s) for s in case["transcript_segments"]]
    assert asyncio.run(MockClinicalExtractionProvider([fact]).extract(segments, [])) == []


def test_mock_document_cites_only_existing_facts(corpus_cases: list[dict[str, Any]]) -> None:
    encounter = encounter_from_case(corpus_cases[91])
    document = asyncio.run(
        MockDocumentGenerationProvider().generate(encounter, "consultation_note")
    )
    assert document.supported_fact_ids == [f.fact_id for f in encounter.facts]
    issues = asyncio.run(MockClinicalValidationProvider().validate(document, encounter))
    assert issues == []


def test_mock_document_on_empty_encounter_is_empty(corpus_cases: list[dict[str, Any]]) -> None:
    encounter = encounter_from_case(corpus_cases[0]).model_copy(update={"facts": []})
    document = asyncio.run(
        MockDocumentGenerationProvider().generate(encounter, "consultation_note")
    )
    assert document.content == ""
    assert document.supported_fact_ids == []


def test_validation_flags_unsupported_claims(corpus_cases: list[dict[str, Any]]) -> None:
    encounter = encounter_from_case(corpus_cases[91])
    forged = GeneratedDocument("consultation_note", "Texte.", ["f1", "f999"])
    issues = asyncio.run(MockClinicalValidationProvider().validate(forged, encounter))
    assert [(i.code, i.fact_id) for i in issues] == [("unknown_fact_id", "f999")]
    unsupported = GeneratedDocument("consultation_note", "Texte sans appui.", [])
    issues = asyncio.run(MockClinicalValidationProvider().validate(unsupported, encounter))
    assert [i.code for i in issues] == ["empty_support"]
