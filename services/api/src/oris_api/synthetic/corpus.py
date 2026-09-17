"""Accès au corpus synthétique (`corpus/synthetic_consultations_100.jsonl`).

Aucun patient réel : le manifeste l'atteste et les tests le vérifient. Le corpus
n'est servi qu'en environnement `local` ou `test`.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from oris_api.contracts import ClinicalFact, Procedure, TranscriptSegment, TreatmentPlan

SYNTHETIC_PAYLOAD_PREFIX = b"oris-synthetic:"


@dataclass(frozen=True)
class SyntheticCase:
    case_id: str
    domain: str
    tags: tuple[str, ...]
    patient_first_name: str
    patient_last_name: str
    segments: tuple[TranscriptSegment, ...]
    facts: tuple[ClinicalFact, ...]
    treatment_plan: TreatmentPlan | None
    procedures: tuple[Procedure, ...]
    expected_warning_codes: tuple[str, ...]


def corpus_path() -> Path:
    override = os.environ.get("ORIS_CORPUS_PATH")
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[5] / "corpus" / "synthetic_consultations_100.jsonl"


def transcript_fingerprint(
    segments: list[TranscriptSegment] | tuple[TranscriptSegment, ...],
) -> str:
    digest = hashlib.sha256()
    for segment in segments:
        digest.update(f"{segment.segment_id}\x1f{segment.text}\x1e".encode())
    return digest.hexdigest()


def parse_case(raw: dict[str, Any]) -> SyntheticCase:
    expected = raw["expected"]
    plan = expected["treatment_plan"]
    return SyntheticCase(
        case_id=raw["case_id"],
        domain=raw["domain"],
        tags=tuple(raw["tags"]),
        patient_first_name=raw["patient"]["first_name"],
        patient_last_name=raw["patient"]["last_name"],
        segments=tuple(TranscriptSegment.model_validate(s) for s in raw["transcript_segments"]),
        facts=tuple(ClinicalFact.model_validate(f) for f in expected["facts"]),
        treatment_plan=TreatmentPlan.model_validate(plan) if plan else None,
        procedures=tuple(Procedure.model_validate(p) for p in expected["procedures"]),
        expected_warning_codes=tuple(w["code"] for w in expected["warnings"]),
    )


class SyntheticCorpus:
    def __init__(self, cases: list[SyntheticCase]) -> None:
        self._by_id = {case.case_id: case for case in cases}
        self._by_fingerprint = {transcript_fingerprint(case.segments): case for case in cases}

    @classmethod
    def load(cls, path: Path | None = None) -> SyntheticCorpus:
        lines = (path or corpus_path()).read_text(encoding="utf-8").splitlines()
        return cls([parse_case(json.loads(line)) for line in lines if line.strip()])

    def cases(self) -> list[SyntheticCase]:
        return list(self._by_id.values())

    def get(self, case_id: str) -> SyntheticCase | None:
        return self._by_id.get(case_id)

    def by_transcript(
        self, segments: list[TranscriptSegment] | tuple[TranscriptSegment, ...]
    ) -> SyntheticCase | None:
        return self._by_fingerprint.get(transcript_fingerprint(segments))


@lru_cache
def default_corpus() -> SyntheticCorpus:
    return SyntheticCorpus.load()
