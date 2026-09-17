"""Exécution du banc d'essai : mêmes fichiers audio pour chaque fournisseur."""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from statistics import fmean
from typing import Any
from uuid import uuid4

from oris_api.benchmark import metrics
from oris_api.benchmark.dataset import Dataset, DatasetItem
from oris_api.contracts import validate_contract
from oris_api.domain.speaker_roles import apply_roles
from oris_api.domain.types import AudioChunk
from oris_api.ontology.stt_glossary import DENTAL_GLOSSARY_FR
from oris_api.providers.base import (
    SpeechToTextProvider,
    StreamingSpeechToTextProvider,
    TranscriptionUnavailable,
)
from oris_api.stt.audio import split_pcm, wav_to_pcm

# Pondération de la note technique ; la conformité est un préalable, pas un bonus.
WEIGHTS = {
    "tooth_number_accuracy": 0.25,
    "critical_term_recall": 0.15,
    "negation_preservation": 0.15,
    "speaker_accuracy": 0.10,
    "wer_score": 0.10,
    "latency_score": 0.10,
    "customization_score": 0.05,
    "reliability": 0.05,
    "cost_score": 0.05,
}
CHUNK_MS = 2000


@dataclass
class ProviderUnderTest:
    key: str
    batch: SpeechToTextProvider
    batch_without_glossary: SpeechToTextProvider | None = None
    streaming: StreamingSpeechToTextProvider | None = None
    usd_per_minute: float | None = None
    compliance_gate: str = "not_reviewed"  # not_reviewed | passed | failed


@dataclass
class ItemScore:
    audio_id: str
    ok: bool
    error_code: str | None = None
    wer: float | None = None
    teeth: metrics.Ratio = field(default_factory=lambda: metrics.Ratio(0, 0))
    hallucinated_teeth: int = 0
    negations: metrics.Ratio = field(default_factory=lambda: metrics.Ratio(0, 0))
    terms: metrics.Ratio = field(default_factory=lambda: metrics.Ratio(0, 0))
    speaker_accuracy: float | None = None
    role_accuracy: float | None = None
    latency_s: float | None = None
    real_time_factor: float | None = None


@dataclass
class StreamingScore:
    interim_latencies_ms: list[float] = field(default_factory=list)
    final_latencies_ms: list[float] = field(default_factory=list)
    reconnections: int = 0
    failures: int = 0
    items: int = 0


@dataclass
class ProviderReport:
    key: str
    version: str
    with_glossary: list[ItemScore]
    without_glossary: list[ItemScore] | None
    streaming: StreamingScore | None
    usd_per_minute: float | None
    compliance_gate: str
    summary: dict[str, float | None] = field(default_factory=dict)
    critical_regressions: list[str] = field(default_factory=list)
    evaluation_run: dict[str, Any] = field(default_factory=dict)


def load_audio(item: DatasetItem) -> list[AudioChunk]:
    pcm, rate = wav_to_pcm(item.audio_path.read_bytes())
    if rate != 16_000:
        raise ValueError(f"{item.audio_id} : 16 kHz attendu, {rate} Hz reçu")
    return split_pcm(pcm, session_id=item.audio_id, chunk_ms=CHUNK_MS)


def score_item(item: DatasetItem, result: Any, latency_s: float) -> ItemScore:
    reference = metrics.tokenize(item.reference_text)
    hypothesis = metrics.tokenize(" ".join(s.text for s in result.segments))
    alignment = metrics.align(reference, hypothesis)
    ref_spans = [metrics.TimedSpan(s.start_ms, s.end_ms, s.role) for s in item.reference_segments]
    labelled = [
        metrics.TimedSpan(s.start_ms, s.end_ms, result.speaker_labels[s.segment_id])
        for s in result.segments
        if s.segment_id in result.speaker_labels
    ]
    with_roles = (
        apply_roles(result.segments, result.speaker_labels) if result.speaker_labels else []
    )
    role_spans = [metrics.TimedSpan(s.start_ms, s.end_ms, s.speaker_role) for s in with_roles]
    return ItemScore(
        audio_id=item.audio_id,
        ok=True,
        wer=alignment.wer,
        teeth=metrics.tooth_accuracy(reference, alignment),
        hallucinated_teeth=metrics.hallucinated_teeth(hypothesis, alignment),
        negations=metrics.negation_preservation(reference, alignment),
        terms=metrics.term_recall(reference, hypothesis, DENTAL_GLOSSARY_FR),
        speaker_accuracy=metrics.speaker_accuracy(ref_spans, labelled),
        role_accuracy=metrics.role_accuracy(ref_spans, role_spans) if role_spans else None,
        latency_s=latency_s,
        real_time_factor=latency_s / (item.duration_ms / 1000) if item.duration_ms else None,
    )


async def run_batch(
    provider: SpeechToTextProvider, dataset: Dataset, concurrency: int = 2
) -> list[ItemScore]:
    semaphore = asyncio.Semaphore(concurrency)

    async def one(item: DatasetItem) -> ItemScore:
        async with semaphore:
            chunks = load_audio(item)
            started = time.perf_counter()
            try:
                result = await provider.transcribe(chunks, dataset.locale, [])
            except TranscriptionUnavailable as error:
                return ItemScore(audio_id=item.audio_id, ok=False, error_code=error.code)
            return score_item(item, result, time.perf_counter() - started)

    return list(await asyncio.gather(*(one(item) for item in dataset.items)))


async def paced(chunks: list[AudioChunk], speed: float) -> AsyncIterator[AudioChunk]:
    """Rejoue l'audio au rythme réel (speed=1) comme pendant une consultation."""
    for chunk in chunks:
        yield chunk
        await asyncio.sleep(CHUNK_MS / 1000 / speed)


async def run_streaming(
    provider: StreamingSpeechToTextProvider, dataset: Dataset, speed: float
) -> StreamingScore:
    score = StreamingScore()
    for item in dataset.items:
        chunks = load_audio(item)
        score.items += 1
        t0 = time.monotonic()
        try:
            async for event in provider.stream(paced(chunks, speed), dataset.locale, []):
                if event.kind == "reconnected":
                    score.reconnections += 1
                    continue
                if event.segment is None:
                    continue
                # Latence = réception - moment où la fin de cette parole a été envoyée.
                spoken_at = t0 + event.audio_end_ms / 1000 / speed
                latency = max(0.0, (event.received_monotonic - spoken_at) * 1000)
                target = (
                    score.final_latencies_ms
                    if event.kind == "final"
                    else score.interim_latencies_ms
                )
                target.append(latency)
        except TranscriptionUnavailable:
            score.failures += 1
    return score


def ratio_total(scores: list[ItemScore], name: str) -> float | None:
    ratios = [getattr(s, name) for s in scores if s.ok]
    total = sum(r.total for r in ratios)
    return sum(r.correct for r in ratios) / total if total else None


def mean(values: list[float | None]) -> float | None:
    present = [v for v in values if v is not None]
    return fmean(present) if present else None


def clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def summarize(report: ProviderReport) -> None:
    scores = report.with_glossary
    ok = [s for s in scores if s.ok]
    summary: dict[str, float | None] = {
        "items": float(len(scores)),
        "reliability": len(ok) / len(scores) if scores else None,
        "wer": mean([s.wer for s in ok]),
        "tooth_number_accuracy": ratio_total(scores, "teeth"),
        "hallucinated_teeth": float(sum(s.hallucinated_teeth for s in ok)),
        "critical_term_recall": ratio_total(scores, "terms"),
        "negation_preservation": ratio_total(scores, "negations"),
        "speaker_accuracy": mean([s.speaker_accuracy for s in ok]),
        "role_accuracy": mean([s.role_accuracy for s in ok]),
        "finalization_latency_p50_s": metrics.percentile(
            [s.latency_s for s in ok if s.latency_s is not None], 50
        ),
        "finalization_latency_p95_s": metrics.percentile(
            [s.latency_s for s in ok if s.latency_s is not None], 95
        ),
        "finalization_rtf_p95": metrics.percentile(
            [s.real_time_factor for s in ok if s.real_time_factor is not None], 95
        ),
    }
    if report.without_glossary is not None:
        base_terms = ratio_total(report.without_glossary, "terms")
        base_teeth = ratio_total(report.without_glossary, "teeth")
        base_wer = mean([s.wer for s in report.without_glossary if s.ok])
        summary["glossary_gain_term_recall"] = _delta(summary["critical_term_recall"], base_terms)
        summary["glossary_gain_tooth_accuracy"] = _delta(
            summary["tooth_number_accuracy"], base_teeth
        )
        summary["glossary_gain_wer"] = _delta(base_wer, summary["wer"])
    if report.streaming is not None:
        stream = report.streaming
        summary["interim_latency_p50_ms"] = metrics.percentile(stream.interim_latencies_ms, 50)
        summary["interim_latency_p95_ms"] = metrics.percentile(stream.interim_latencies_ms, 95)
        summary["final_latency_p50_ms"] = metrics.percentile(stream.final_latencies_ms, 50)
        summary["final_latency_p95_ms"] = metrics.percentile(stream.final_latencies_ms, 95)
        summary["stream_reconnections"] = float(stream.reconnections)
        summary["stream_failures"] = float(stream.failures)
    summary["cost_usd_per_30_min"] = (
        report.usd_per_minute * 30 if report.usd_per_minute is not None else None
    )

    # Sous-scores 0…1 (règles documentées dans le rapport).
    subscores: dict[str, float | None] = {
        "tooth_number_accuracy": summary["tooth_number_accuracy"],
        "critical_term_recall": summary["critical_term_recall"],
        "negation_preservation": summary["negation_preservation"],
        "speaker_accuracy": summary["speaker_accuracy"],
        "wer_score": clamp(1 - summary["wer"]) if summary["wer"] is not None else None,
        "latency_score": latency_score(summary),
        "customization_score": (
            (1.0 if (summary["glossary_gain_term_recall"] or 0) >= 0 else 0.5)
            if summary.get("glossary_gain_term_recall") is not None
            else None
        ),
        "reliability": summary["reliability"],
        "cost_score": (
            clamp(1 - summary["cost_usd_per_30_min"] / 10)
            if summary["cost_usd_per_30_min"] is not None
            else None
        ),
    }
    available = {k: v for k, v in subscores.items() if v is not None}
    weight = sum(WEIGHTS[k] for k in available)
    summary["weighted_score"] = (
        sum(WEIGHTS[k] * v for k, v in available.items()) / weight if weight else None
    )
    summary["weighted_score_coverage"] = weight
    report.summary = summary

    report.critical_regressions = sorted(
        {
            f"{s.audio_id}:tooth_number"
            for s in ok
            if s.teeth.total and s.teeth.correct < s.teeth.total
        }
        | {f"{s.audio_id}:tooth_hallucinated" for s in ok if s.hallucinated_teeth}
        | {
            f"{s.audio_id}:negation_lost"
            for s in ok
            if s.negations.total and s.negations.correct < s.negations.total
        }
        | {f"{s.audio_id}:failed:{s.error_code}" for s in scores if not s.ok}
    )


def latency_score(summary: dict[str, float | None]) -> float | None:
    """Direct mesuré : 1 − p95/3 s. Sinon : 1 − (délai de finalisation / durée audio)."""
    interim = summary.get("interim_latency_p95_ms")
    if interim is not None:
        return clamp(1 - interim / 3000)
    rtf = summary.get("finalization_rtf_p95")
    return clamp(1 - rtf) if rtf is not None else None


def _delta(value: float | None, baseline: float | None) -> float | None:
    return value - baseline if value is not None and baseline is not None else None


def evaluation_run(report: ProviderReport, dataset: Dataset) -> dict[str, Any]:
    run = {
        "evaluation_run_id": str(uuid4()),
        "component": f"stt:{report.key}",
        "candidate_version": report.version,
        "dataset_version": f"{dataset.name}@{dataset.version}",
        "metrics": {k: v for k, v in report.summary.items() if v is not None},
        "critical_regressions": report.critical_regressions,
        "created_at": datetime.now(UTC).isoformat(),
        # Choix possible seulement si la conformité est validée et sans régression critique.
        "release_gate_passed": report.compliance_gate == "passed"
        and not report.critical_regressions,
    }
    validate_contract("EvaluationRun", run)
    return run


async def run_benchmark(
    dataset: Dataset,
    providers: list[ProviderUnderTest],
    streaming: bool = False,
    speed: float = 1.0,
) -> list[ProviderReport]:
    dataset.ensure_allowed()
    reports = []
    for candidate in providers:
        report = ProviderReport(
            key=candidate.key,
            version=candidate.batch.info.version,
            with_glossary=await run_batch(candidate.batch, dataset),
            without_glossary=(
                await run_batch(candidate.batch_without_glossary, dataset)
                if candidate.batch_without_glossary is not None
                else None
            ),
            streaming=(
                await run_streaming(candidate.streaming, dataset, speed)
                if streaming and candidate.streaming is not None
                else None
            ),
            usd_per_minute=candidate.usd_per_minute,
            compliance_gate=candidate.compliance_gate,
        )
        summarize(report)
        report.evaluation_run = evaluation_run(report, dataset)
        reports.append(report)
    return reports


def write_outputs(reports: list[ProviderReport], dataset: Dataset, directory: Path) -> Path:
    from oris_api.benchmark.report import render_markdown

    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    runs = [report.evaluation_run for report in reports]
    (directory / f"{stamp}-{dataset.name}.json").write_text(
        json.dumps(runs, indent=2, ensure_ascii=False)
    )
    markdown = directory / f"{stamp}-{dataset.name}.md"
    markdown.write_text(render_markdown(reports, dataset))
    return markdown
