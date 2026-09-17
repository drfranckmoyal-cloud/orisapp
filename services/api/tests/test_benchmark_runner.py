"""Banc d'essai de bout en bout avec des fournisseurs simulés (sans réseau)."""

from __future__ import annotations

import asyncio
import json
import time
import wave
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest

from oris_api.benchmark.dataset import Dataset, DatasetNotAllowed
from oris_api.benchmark.runner import ProviderUnderTest, run_benchmark, write_outputs
from oris_api.contracts import TranscriptSegment, validate_contract
from oris_api.domain.types import AudioChunk, GlossaryHint, TranscriptionResult
from oris_api.providers.base import ProviderInfo, StreamEvent, TranscriptionUnavailable

REFERENCES = {
    "a1": [
        {
            "role": "patient",
            "start_ms": 0,
            "end_ms": 2000,
            "text": "Je n'ai pas de douleur nocturne.",
        },
        {
            "role": "practitioner",
            "start_ms": 2400,
            "end_ms": 5000,
            "text": "Sur la vingt-sept, restauration fracturée, Filtek Supreme XTE prévu.",
        },
    ],
    "a2": [
        {
            "role": "practitioner",
            "start_ms": 0,
            "end_ms": 3000,
            "text": "Je note une fissure sur la 16, composite proposé après examen.",
        },
        {
            "role": "patient",
            "start_ms": 3400,
            "end_ms": 5000,
            "text": "Je ne veux pas de couronne.",
        },
    ],
}


def make_dataset(tmp_path: Path, synthetic: bool = True) -> Path:
    (tmp_path / "audio").mkdir()
    items = []
    for audio_id, refs in REFERENCES.items():
        with wave.open(str(tmp_path / "audio" / f"{audio_id}.wav"), "wb") as out:
            out.setnchannels(1)
            out.setsampwidth(2)
            out.setframerate(16_000)
            out.writeframes(b"\x00\x00" * 16 * 5000)
        items.append(
            {
                "audio_id": audio_id,
                "audio_file": f"audio/{audio_id}.wav",
                "duration_ms": 5000,
                "reference_segments": refs,
            }
        )
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps({"name": "test", "version": "1", "synthetic_only": synthetic, "items": items})
    )
    return manifest


def audio_id(chunks: list[AudioChunk]) -> str:
    return chunks[0].session_id


class Oracle:
    """Renvoie exactement la référence (avec étiquettes de locuteur arbitraires)."""

    info = ProviderInfo("oracle", "1")

    def __init__(self, alter: Any = None, fail_on: str | None = None) -> None:
        self.alter = alter or (lambda text: text)
        self.fail_on = fail_on

    async def transcribe(
        self, chunks: list[AudioChunk], locale: str, glossary: list[GlossaryHint]
    ) -> TranscriptionResult:
        key = audio_id(chunks)
        if key == self.fail_on:
            raise TranscriptionUnavailable("TEST_OUTAGE")
        segments, labels = [], {}
        for index, ref in enumerate(REFERENCES[key]):
            segment_id = f"t{index + 1}"
            segments.append(
                TranscriptSegment(
                    segment_id=segment_id,
                    start_ms=ref["start_ms"],
                    end_ms=ref["end_ms"],
                    speaker_role="unknown",
                    text=self.alter(ref["text"]),
                    confidence=0.9,
                    is_final=True,
                )
            )
            labels[segment_id] = "S1" if ref["role"] == "practitioner" else "S2"
        return TranscriptionResult(segments, speaker_labels=labels)


class StreamingOracle:
    info = ProviderInfo("oracle", "stream")

    async def stream(
        self, chunks: AsyncIterator[AudioChunk], locale: str, glossary: list[GlossaryHint]
    ) -> AsyncIterator[StreamEvent]:
        async for chunk in chunks:
            end = chunk.timestamp_ms + len(chunk.payload) // 32
            seg = TranscriptSegment(
                segment_id="t1",
                start_ms=chunk.timestamp_ms,
                end_ms=end,
                speaker_role="unknown",
                text="texte",
                confidence=0.9,
                is_final=False,
            )
            yield StreamEvent("interim", seg, "S1", end, time.monotonic())
        yield StreamEvent(
            "final", seg.model_copy(update={"is_final": True}), "S1", end, time.monotonic()
        )


def test_perfect_provider_scores_perfectly(tmp_path: Path) -> None:
    dataset = Dataset.load(make_dataset(tmp_path))
    candidate = ProviderUnderTest(
        "oracle",
        Oracle(),
        Oracle(),
        StreamingOracle(),
        usd_per_minute=0.01,
        compliance_gate="passed",
    )
    [report] = asyncio.run(run_benchmark(dataset, [candidate], streaming=True, speed=50))
    summary = report.summary
    assert summary["wer"] == 0
    assert summary["tooth_number_accuracy"] == 1
    assert summary["negation_preservation"] == 1
    assert summary["critical_term_recall"] == 1
    assert summary["speaker_accuracy"] == 1
    assert summary["role_accuracy"] is not None
    assert summary["reliability"] == 1
    assert summary["cost_usd_per_30_min"] == pytest.approx(0.3)
    assert summary["interim_latency_p95_ms"] is not None
    assert summary["weighted_score_coverage"] == pytest.approx(1.0)
    assert report.critical_regressions == []
    assert report.evaluation_run["release_gate_passed"] is True
    validate_contract("EvaluationRun", report.evaluation_run)


def test_tooth_and_negation_errors_are_critical_regressions(tmp_path: Path) -> None:
    dataset = Dataset.load(make_dataset(tmp_path))

    def degrade(text: str) -> str:
        return text.replace("vingt-sept", "vingt-six").replace("n'ai pas", "ai")

    candidate = ProviderUnderTest("degraded", Oracle(alter=degrade))
    [report] = asyncio.run(run_benchmark(dataset, [candidate]))
    assert report.summary["tooth_number_accuracy"] == pytest.approx(0.5)
    assert report.summary["hallucinated_teeth"] == 1
    negations = report.summary["negation_preservation"]
    assert negations is not None and negations < 1
    assert "a1:tooth_number" in report.critical_regressions
    assert "a1:negation_lost" in report.critical_regressions
    assert (
        report.evaluation_run["release_gate_passed"] is False
    )  # conformité non évaluée, erreurs critiques


def test_outage_lowers_reliability_and_is_reported(tmp_path: Path) -> None:
    dataset = Dataset.load(make_dataset(tmp_path))
    [report] = asyncio.run(
        run_benchmark(dataset, [ProviderUnderTest("flaky", Oracle(fail_on="a2"))])
    )
    assert report.summary["reliability"] == 0.5
    assert "a2:failed:TEST_OUTAGE" in report.critical_regressions


def test_glossary_gain_is_measured(tmp_path: Path) -> None:
    dataset = Dataset.load(make_dataset(tmp_path))
    without = Oracle(alter=lambda t: t.replace("Filtek Supreme XTE", "filtre suprême"))
    [report] = asyncio.run(run_benchmark(dataset, [ProviderUnderTest("g", Oracle(), without)]))
    # 4 termes du glossaire présents (Filtek, restauration fracturée, composite, fissure) :
    # sans glossaire la marque est manquée → 3/4 ; avec → 4/4.
    assert report.summary["glossary_gain_term_recall"] == pytest.approx(0.25)


def test_missing_price_is_excluded_not_invented(tmp_path: Path) -> None:
    dataset = Dataset.load(make_dataset(tmp_path))
    [report] = asyncio.run(run_benchmark(dataset, [ProviderUnderTest("p", Oracle())]))
    assert report.summary["cost_usd_per_30_min"] is None
    coverage = report.summary["weighted_score_coverage"]
    assert coverage is not None and coverage < 1


def test_report_is_written_in_french_and_flags_synthetic_data(tmp_path: Path) -> None:
    (tmp_path / "data").mkdir()
    dataset = Dataset.load(make_dataset(tmp_path / "data"))
    reports = asyncio.run(run_benchmark(dataset, [ProviderUnderTest("oracle", Oracle())]))
    markdown = write_outputs(reports, dataset, tmp_path / "reports")
    text = markdown.read_text()
    assert "Données synthétiques" in text
    assert "Numéros de dent exacts" in text
    assert "Aucun fournisseur n'est choisi" in text
    runs = json.loads(markdown.with_suffix(".json").read_text())
    validate_contract("EvaluationRun", runs[0])


def test_real_recordings_without_consent_are_refused(tmp_path: Path) -> None:
    with pytest.raises(DatasetNotAllowed):
        Dataset.load(make_dataset(tmp_path, synthetic=False))
