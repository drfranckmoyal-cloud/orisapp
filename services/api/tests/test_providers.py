"""Fournisseurs factices : configuration, contrat, absence d'invention."""

from __future__ import annotations

import asyncio
import hashlib

import pytest

from oris_api.config import Settings
from oris_api.contracts import ClinicalEncounter
from oris_api.domain.types import AudioChunk, Claim, GeneratedDocument
from oris_api.providers import (
    ClinicalExtractionProvider,
    ClinicalValidationProvider,
    DocumentGenerationProvider,
    SpeechToTextProvider,
    build_providers,
)
from oris_api.providers.mock import (
    MockClinicalExtractionProvider,
    MockClinicalValidationProvider,
    MockSpeechToTextProvider,
)
from oris_api.synthetic.corpus import SYNTHETIC_PAYLOAD_PREFIX, SyntheticCorpus, default_corpus


def chunk(payload: bytes) -> AudioChunk:
    return AudioChunk("s", 0, 0, hashlib.sha256(payload).hexdigest(), payload)


def encounter_for(case_id: str) -> ClinicalEncounter:
    case = default_corpus().get(case_id)
    assert case is not None
    return ClinicalEncounter(
        encounter_id="enc",
        patient_id="pat",
        practitioner_id="usr",
        started_at="2026-09-17T09:00:00Z",
        ended_at=None,
        status="review",
        object_version=1,
        facts=list(case.facts),
        treatment_plan=case.treatment_plan,
        procedures=list(case.procedures),
        warnings=[],
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


def test_corpus_is_not_served_outside_local_and_test() -> None:
    providers = build_providers(Settings(app_env="staging"))
    payload = SYNTHETIC_PAYLOAD_PREFIX + b"ORIS-SYN-091"
    result = asyncio.run(providers.speech_to_text.transcribe([chunk(payload)], "fr-FR", []))
    assert result.segments == []


def test_mock_stt_decodes_synthetic_chunk() -> None:
    provider = MockSpeechToTextProvider(default_corpus())
    payload = SYNTHETIC_PAYLOAD_PREFIX + b"ORIS-SYN-091"
    result = asyncio.run(provider.transcribe([chunk(payload)], "fr-FR", []))
    assert [s.segment_id for s in result.segments] == ["s1", "s2"]
    assert result.gaps == []


def test_mock_stt_reports_audio_gap_instead_of_hiding_it() -> None:
    provider = MockSpeechToTextProvider(default_corpus())
    payload = SYNTHETIC_PAYLOAD_PREFIX + b"ORIS-SYN-099"
    result = asyncio.run(provider.transcribe([chunk(payload)], "fr-FR", []))
    assert len(result.gaps) == 1
    assert result.gaps[0].after_segment_id == "s1"


def test_mock_stt_ignores_real_audio() -> None:
    provider = MockSpeechToTextProvider(default_corpus())
    result = asyncio.run(provider.transcribe([chunk(b"\x00\x01audio")], "fr-FR", []))
    assert result.segments == []


def test_mock_extraction_invents_nothing_for_unknown_transcript() -> None:
    case = default_corpus().get("ORIS-SYN-091")
    assert case is not None
    altered = [case.segments[0].model_copy(update={"text": "Autre chose."}), case.segments[1]]
    result = asyncio.run(MockClinicalExtractionProvider(default_corpus()).extract(altered, []))
    assert result.facts == []
    assert result.treatment_plan is None


def test_empty_corpus_extracts_nothing() -> None:
    case = default_corpus().get("ORIS-SYN-091")
    assert case is not None
    provider = MockClinicalExtractionProvider(SyntheticCorpus([]))
    assert asyncio.run(provider.extract(list(case.segments), [])).facts == []


def test_validation_provider_flags_unsupported_claims() -> None:
    encounter = encounter_for("ORIS-SYN-092")
    forged = GeneratedDocument(
        "consultation_note",
        "Texte.",
        (
            Claim("S", "Rapporté : sensibilité (16).", fact_ids=("f1", "f999")),
            Claim("S", "Phrase sans appui."),
        ),
    )
    issues = asyncio.run(MockClinicalValidationProvider().validate(forged, encounter))
    codes = {(i.code, i.fact_id) for i in issues}
    assert ("unknown_fact_id", "f999") in codes
    assert ("unsupported_claim", None) in codes
