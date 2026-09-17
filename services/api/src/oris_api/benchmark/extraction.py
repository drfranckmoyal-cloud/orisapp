"""Banc d'essai de l'extraction clinique (TECHNICAL_BENCHMARK, « Extraction benchmark »).

Compare la sortie d'un modèle aux faits attendus des 100 consultations du corpus.
Aucun audio : on part des transcripts, la transcription est mesurée à part.
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4

from oris_api.benchmark.metrics import percentile
from oris_api.contracts import ClinicalFact, TranscriptSegment, validate_contract
from oris_api.domain.resolver import resolve
from oris_api.domain.types import ExtractionResult, GlossaryHint
from oris_api.ontology.labels import label_for
from oris_api.providers.base import ExtractionUnavailable
from oris_api.synthetic.corpus import SyntheticCase


class ExtractionProvider(Protocol):
    async def extract(
        self, segments: list[TranscriptSegment], glossary: list[GlossaryHint]
    ) -> ExtractionResult: ...


def identity(fact: ClinicalFact) -> tuple[str, tuple[str, ...]]:
    """Deux faits parlent de la même chose s'ils ont le même concept et les mêmes dents."""
    return fact.concept.strip().lower(), tuple(sorted(fact.teeth))


@dataclass
class CaseScore:
    case_id: str
    ok: bool
    error_code: str | None = None
    expected: int = 0
    produced: int = 0
    matched: int = 0
    duplicates: int = 0
    negation_correct: int = 0
    negation_total: int = 0
    temporality_correct: int = 0
    temporality_total: int = 0
    status_correct: int = 0
    status_total: int = 0
    plan_status_correct: int = 0
    plan_status_total: int = 0
    unknown_teeth: int = 0
    renderable: int = 0
    resolver_rules: tuple[str, ...] = ()
    retried: bool = False
    latency_s: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0


def score_case(case: SyntheticCase, result: ExtractionResult, latency_s: float) -> CaseScore:
    expected = {identity(fact): fact for fact in case.facts}
    produced_keys = [identity(fact) for fact in result.facts]
    score = CaseScore(
        case_id=case.case_id,
        ok=True,
        expected=len(expected),
        produced=len(result.facts),
        duplicates=len(produced_keys) - len(set(produced_keys)),
        latency_s=latency_s,
        input_tokens=(result.usage or {}).get("input_tokens", 0),
        output_tokens=(result.usage or {}).get("output_tokens", 0),
    )
    reference_teeth = {tooth for fact in case.facts for tooth in fact.teeth}
    score.renderable = sum(
        1 for fact in result.facts if label_for(fact.concept, fact.category) is not None
    )
    seen: set[tuple[str, tuple[str, ...]]] = set()
    for fact in result.facts:
        key = identity(fact)
        score.unknown_teeth += sum(1 for tooth in fact.teeth if tooth not in reference_teeth)
        reference = expected.get(key)
        if reference is None or key in seen:
            continue
        seen.add(key)
        score.matched += 1
        # Axes cliniques : comparés uniquement sur les faits retrouvés.
        score.negation_total += 1
        score.negation_correct += fact.assertion == reference.assertion
        score.temporality_total += 1
        score.temporality_correct += fact.temporality == reference.temporality
        score.status_total += 1
        score.status_correct += fact.clinical_status == reference.clinical_status
        if reference.clinical_status in {"planned", "performed"}:
            score.plan_status_total += 1
            score.plan_status_correct += fact.clinical_status == reference.clinical_status
    violations = resolve(
        result.facts, result.treatment_plan, result.procedures, list(case.segments), True
    )
    score.resolver_rules = tuple(sorted({v.rule for v in violations}))
    return score


@dataclass
class ModelReport:
    key: str
    version: str
    scores: list[CaseScore]
    usd_per_million_input: float | None = None
    usd_per_million_output: float | None = None
    summary: dict[str, float | None] = field(default_factory=dict)
    critical_regressions: list[str] = field(default_factory=list)
    evaluation_run: dict[str, Any] = field(default_factory=dict)


def ratio(correct: int, total: int) -> float | None:
    return correct / total if total else None


def summarize(report: ModelReport) -> None:
    scores = report.scores
    ok = [s for s in scores if s.ok]
    produced = sum(s.produced for s in ok)
    expected = sum(s.expected for s in ok)
    matched = sum(s.matched for s in ok)
    tokens_in = sum(s.input_tokens for s in ok)
    tokens_out = sum(s.output_tokens for s in ok)
    summary: dict[str, float | None] = {
        "cases": float(len(scores)),
        "reliability": ratio(len(ok), len(scores)),
        "fact_precision": ratio(matched, produced),
        "fact_recall": ratio(matched, expected),
        "duplicate_fact_rate": ratio(sum(s.duplicates for s in ok), produced),
        "negation_accuracy": ratio(
            sum(s.negation_correct for s in ok), sum(s.negation_total for s in ok)
        ),
        "temporality_accuracy": ratio(
            sum(s.temporality_correct for s in ok), sum(s.temporality_total for s in ok)
        ),
        "status_accuracy": ratio(
            sum(s.status_correct for s in ok), sum(s.status_total for s in ok)
        ),
        "plan_vs_performed_accuracy": ratio(
            sum(s.plan_status_correct for s in ok), sum(s.plan_status_total for s in ok)
        ),
        "unknown_teeth": float(sum(s.unknown_teeth for s in ok)),
        "renderable_fact_rate": ratio(sum(s.renderable for s in ok), produced),
        "resolver_rejection_rate": ratio(sum(1 for s in ok if s.resolver_rules), len(ok)),
        "schema_valid_first_try": ratio(sum(1 for s in ok if not s.retried), len(ok)),
        "latency_p50_s": percentile([s.latency_s for s in ok], 50),
        "latency_p95_s": percentile([s.latency_s for s in ok], 95),
        "input_tokens_mean": ratio(tokens_in, len(ok)),
        "output_tokens_mean": ratio(tokens_out, len(ok)),
    }
    if (
        report.usd_per_million_input is not None
        and report.usd_per_million_output is not None
        and ok
    ):
        cost = (
            tokens_in * report.usd_per_million_input + tokens_out * report.usd_per_million_output
        ) / 1_000_000
        summary["cost_usd_per_consultation"] = cost / len(ok)
    report.summary = summary
    report.critical_regressions = sorted(
        {f"{s.case_id}:rejected:{s.error_code}" for s in scores if not s.ok}
        | {f"{s.case_id}:resolver:{rule}" for s in ok for rule in s.resolver_rules}
        | {f"{s.case_id}:unknown_teeth" for s in ok if s.unknown_teeth}
        | {
            f"{s.case_id}:negation_lost"
            for s in ok
            if s.negation_total and s.negation_correct < s.negation_total
        }
    )
    run = {
        "evaluation_run_id": str(uuid4()),
        "component": f"clinical_extraction:{report.key}",
        "candidate_version": report.version,
        "dataset_version": "oris-synthetic-corpus@1.0",
        "metrics": {k: v for k, v in summary.items() if v is not None},
        "critical_regressions": report.critical_regressions,
        "created_at": datetime.now(UTC).isoformat(),
        # Aucun modèle n'est retenu tant que la conformité n'est pas évaluée (D020, §66).
        "release_gate_passed": False,
    }
    validate_contract("EvaluationRun", run)
    report.evaluation_run = run


async def run_model(
    provider: ExtractionProvider, cases: list[SyntheticCase], concurrency: int = 3
) -> list[CaseScore]:
    semaphore = asyncio.Semaphore(concurrency)

    async def one(case: SyntheticCase) -> CaseScore:
        async with semaphore:
            started = time.perf_counter()
            try:
                result = await provider.extract(list(case.segments), [])
            except ExtractionUnavailable as error:
                return CaseScore(case_id=case.case_id, ok=False, error_code=error.code)
            return score_case(case, result, time.perf_counter() - started)

    return list(await asyncio.gather(*(one(case) for case in cases)))


LABELS = {
    "cases": "Consultations",
    "reliability": "Extractions abouties",
    "fact_precision": "Précision des faits (justes parmi produits)",
    "fact_recall": "Rappel des faits (attendus retrouvés)",
    "duplicate_fact_rate": "Faits produits en double",
    "negation_accuracy": "Négations justes",
    "temporality_accuracy": "Temporalité juste",
    "status_accuracy": "Statut clinique juste",
    "plan_vs_performed_accuracy": "Prévu / réalisé juste",
    "unknown_teeth": "Dents citées absentes de la référence",
    "renderable_fact_rate": "Faits qu'Oris sait rédiger (concept connu)",
    "resolver_rejection_rate": "Sorties rejetées par le résolveur",
    "schema_valid_first_try": "Schéma respecté du premier coup",
    "latency_p50_s": "Délai médian (s)",
    "latency_p95_s": "Délai 95e centile (s)",
    "input_tokens_mean": "Jetons reçus par consultation",
    "output_tokens_mean": "Jetons produits par consultation",
    "cost_usd_per_consultation": "Coût par consultation (USD)",
}
PERCENT = {
    "reliability",
    "fact_precision",
    "fact_recall",
    "duplicate_fact_rate",
    "negation_accuracy",
    "temporality_accuracy",
    "status_accuracy",
    "plan_vs_performed_accuracy",
    "resolver_rejection_rate",
    "renderable_fact_rate",
    "schema_valid_first_try",
}


def render_markdown(reports: list[ModelReport], case_count: int) -> str:
    lines = [
        "# Banc d'essai extraction clinique — corpus synthétique Oris",
        "",
        f"{case_count} consultation(s), transcripts du corpus (sans audio).",
        "",
        "> **Données synthétiques.** Consultations écrites pour ce projet : ce banc mesure la "
        "fidélité de l'extraction, il ne remplace pas une évaluation sur consultations réelles.",
        "",
        "## Résultats",
        "",
        "| Mesure | " + " | ".join(f"{r.key}" for r in reports) + " |",
        "|---|" + "---|" * len(reports),
    ]
    for key, label in LABELS.items():
        if all(r.summary.get(key) is None for r in reports):
            continue
        values = []
        for report in reports:
            value = report.summary.get(key)
            if value is None:
                values.append("non mesuré")
            elif key in PERCENT:
                values.append(f"{value * 100:.1f} %")
            elif key == "cost_usd_per_consultation":
                values.append(f"{value:.4f}")
            else:
                values.append(f"{value:.2f}" if value % 1 else f"{value:.0f}")
        lines.append(f"| {label} | " + " | ".join(values) + " |")
    lines += ["", "## Erreurs critiques", ""]
    for report in reports:
        regressions = report.critical_regressions
        lines.append(
            f"- {report.key} : {len(regressions)} — " + (", ".join(regressions[:15]) or "aucune")
        )
    lines += [
        "",
        "## Méthode",
        "",
        "- Un fait produit correspond à un fait attendu s'il porte le **même concept et les mêmes "
        "dents** ; les axes (négation, temporalité, statut) sont ensuite comparés sur ces faits.",
        "- Le résolveur déterministe d'Oris est appliqué à chaque sortie : toute violation est "
        "comptée comme une régression critique (la sortie serait refusée en production).",
        "- Aucun modèle n'est retenu par ce rapport : la conformité et l'évaluation sur "
        "consultations réelles restent des préalables.",
    ]
    return "\n".join(lines) + "\n"


def write_outputs(reports: list[ModelReport], case_count: int, directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    (directory / f"{stamp}-extraction.json").write_text(
        json.dumps([r.evaluation_run for r in reports], indent=2, ensure_ascii=False)
    )
    markdown = directory / f"{stamp}-extraction.md"
    markdown.write_text(render_markdown(reports, case_count))
    return markdown
