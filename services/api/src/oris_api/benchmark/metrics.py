"""Métriques du banc d'essai STT (docs/TECHNICAL_BENCHMARK.md). Pures et déterministes."""

from __future__ import annotations

import itertools
import math
import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from oris_api.domain.dental_numbers import FDI, normalize_tooth_numbers

NEGATIONS = frozenset(
    {"ne", "n'", "pas", "plus", "jamais", "aucun", "aucune", "sans", "rien", "ni", "non"}
)
TOKEN = re.compile(r"[0-9a-zà-ÿœæç]+'?")


def tokenize(text: str) -> list[str]:
    """Minuscules, apostrophes unifiées, élisions séparées (« n'ai » → n' ai), dents en chiffres."""
    text = unicodedata.normalize("NFC", text).lower().replace("’", "'").replace("-", " ")
    tokens = TOKEN.findall(text)
    return normalize_tooth_numbers(tokens)


Op = Literal["match", "substitution", "deletion", "insertion"]


@dataclass(frozen=True)
class Alignment:
    ops: list[tuple[Op, int | None, int | None]]  # (opération, index référence, index hypothèse)
    reference_length: int

    @property
    def errors(self) -> int:
        return sum(1 for op, _, _ in self.ops if op != "match")

    @property
    def wer(self) -> float:
        if self.reference_length == 0:
            return 0.0 if self.errors == 0 else 1.0
        return self.errors / self.reference_length

    def matched_reference_indexes(self) -> set[int]:
        return {r for op, r, _ in self.ops if op == "match" and r is not None}


def align(reference: Sequence[str], hypothesis: Sequence[str]) -> Alignment:
    """Alignement de Levenshtein mot à mot avec retour arrière."""
    n, m = len(reference), len(hypothesis)
    cost = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        cost[i][0] = i
    for j in range(m + 1):
        cost[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            same = reference[i - 1] == hypothesis[j - 1]
            cost[i][j] = min(
                cost[i - 1][j - 1] + (0 if same else 1),
                cost[i - 1][j] + 1,
                cost[i][j - 1] + 1,
            )
    ops: list[tuple[Op, int | None, int | None]] = []
    i, j = n, m
    while i > 0 or j > 0:
        if (
            i > 0
            and j > 0
            and cost[i][j] == cost[i - 1][j - 1] + (reference[i - 1] != hypothesis[j - 1])
        ):
            ops.append(
                ("match" if reference[i - 1] == hypothesis[j - 1] else "substitution", i - 1, j - 1)
            )
            i, j = i - 1, j - 1
        elif i > 0 and cost[i][j] == cost[i - 1][j] + 1:
            ops.append(("deletion", i - 1, None))
            i -= 1
        else:
            ops.append(("insertion", None, j - 1))
            j -= 1
    ops.reverse()
    return Alignment(ops, n)


@dataclass(frozen=True)
class Ratio:
    correct: int
    total: int

    @property
    def value(self) -> float | None:
        return self.correct / self.total if self.total else None


def tooth_accuracy(reference: list[str], alignment: Alignment) -> Ratio:
    """Numéros de dent de la référence retrouvés exactement à leur place."""
    positions = [i for i, token in enumerate(reference) if FDI.match(token)]
    matched = alignment.matched_reference_indexes()
    return Ratio(sum(1 for i in positions if i in matched), len(positions))


def hallucinated_teeth(hypothesis: list[str], alignment: Alignment) -> int:
    """Numéros de dent écrits par le STT sans correspondance exacte dans la référence."""
    wrong = 0
    for op, _, h in alignment.ops:
        if h is not None and op in {"substitution", "insertion"} and FDI.match(hypothesis[h]):
            wrong += 1
    return wrong


def negation_preservation(reference: list[str], alignment: Alignment) -> Ratio:
    positions = [i for i, token in enumerate(reference) if token in NEGATIONS]
    matched = alignment.matched_reference_indexes()
    return Ratio(sum(1 for i in positions if i in matched), len(positions))


def contains_sequence(haystack: list[str], needle: list[str]) -> bool:
    if not needle:
        return False
    return any(
        haystack[i : i + len(needle)] == needle for i in range(len(haystack) - len(needle) + 1)
    )


def term_recall(reference: list[str], hypothesis: list[str], terms: Sequence[str]) -> Ratio:
    """Termes critiques (matériaux, marques, actes) présents dans la référence et retrouvés."""
    present = [tokenize(term) for term in terms if contains_sequence(reference, tokenize(term))]
    return Ratio(sum(1 for term in present if contains_sequence(hypothesis, term)), len(present))


@dataclass(frozen=True)
class TimedSpan:
    start_ms: int
    end_ms: int
    label: str


def overlap(a: TimedSpan, b: TimedSpan) -> int:
    return max(0, min(a.end_ms, b.end_ms) - max(a.start_ms, b.start_ms))


def speaker_accuracy(reference: list[TimedSpan], hypothesis: list[TimedSpan]) -> float | None:
    """Part du temps de parole attribuée au bon locuteur, après la meilleure correspondance
    entre étiquettes du fournisseur et locuteurs de la référence."""
    total = sum(span.end_ms - span.start_ms for span in reference)
    if total <= 0:
        return None
    ref_labels = sorted({s.label for s in reference})
    hyp_labels = sorted({s.label for s in hypothesis})
    if not hyp_labels:
        return 0.0
    matrix = {
        (h, r): sum(
            overlap(hs, rs)
            for hs in hypothesis
            if hs.label == h
            for rs in reference
            if rs.label == r
        )
        for h in hyp_labels
        for r in ref_labels
    }
    # Meilleure correspondance injective (peu d'étiquettes : énumération exhaustive).
    best = 0
    if len(hyp_labels) <= len(ref_labels):
        for roles in itertools.permutations(ref_labels, len(hyp_labels)):
            best = max(best, sum(matrix[(h, r)] for h, r in zip(hyp_labels, roles, strict=True)))
    else:
        for labels in itertools.permutations(hyp_labels, len(ref_labels)):
            best = max(best, sum(matrix[(h, r)] for h, r in zip(labels, ref_labels, strict=True)))
    return best / total


def role_accuracy(reference: list[TimedSpan], hypothesis: list[TimedSpan]) -> float | None:
    """Rôles déduits par Oris (praticien/patient) comparés à la référence, sans permutation."""
    total = sum(span.end_ms - span.start_ms for span in reference)
    if total <= 0:
        return None
    correct = sum(overlap(h, r) for h in hypothesis for r in reference if h.label == r.label)
    return min(1.0, correct / total)


def percentile(values: Sequence[float], rank: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, math.ceil(rank / 100 * len(ordered)) - 1)
    return ordered[index]
