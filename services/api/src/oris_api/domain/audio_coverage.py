"""Couverture audio d'une consultation : ce qui a été capté, ce qui manque (spec §69).

Pur et déterministe. Un segment PCM porte son horodatage d'enregistrement (temps
écouté, pauses exclues) et sa durée exacte : deux segments consécutifs doivent se
suivre sans trou. Toute perte non récupérée devient un `AudioGap`, qui produit une
alerte critique : Oris ne présente jamais une consultation incomplète comme entière.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from oris_api.domain.types import AudioGap

# Tolérance d'arrondi entre deux segments (horloges, arrondis de ms).
CONTINUITY_TOLERANCE_MS = 50


@dataclass(frozen=True)
class ChunkInfo:
    sequence: int
    timestamp_ms: int
    duration_ms: int


@dataclass(frozen=True)
class ReportedGap:
    """Interruption signalée par le client (micro perdu, page rechargée)."""

    reason: str
    duration_ms: int | None


@dataclass(frozen=True)
class Coverage:
    received_count: int
    last_sequence: int | None
    missing_sequences: list[int]
    received_duration_ms: int
    gaps: list[AudioGap] = field(default_factory=list)

    @property
    def complete(self) -> bool:
        return not self.missing_sequences and not self.gaps


def compute_coverage(
    chunks: list[ChunkInfo],
    final_sequence: int | None = None,
    reported: list[ReportedGap] | None = None,
) -> Coverage:
    """`final_sequence` : dernier numéro annoncé par le client à la fin (None en cours)."""
    ordered = sorted(chunks, key=lambda c: c.sequence)
    received = {c.sequence for c in ordered}
    last = max(received) if received else None
    expected_last = final_sequence if final_sequence is not None else last
    missing = (
        [s for s in range(expected_last + 1) if s not in received]
        if expected_last is not None
        else []
    )

    gaps: list[AudioGap] = []
    missing_set = set(missing)
    previous: ChunkInfo | None = None
    for chunk in ordered:
        if previous is not None:
            expected_start = previous.timestamp_ms + previous.duration_ms
            hole = chunk.timestamp_ms - expected_start
            skipped = any(s in missing_set for s in range(previous.sequence + 1, chunk.sequence))
            if skipped or hole > CONTINUITY_TOLERANCE_MS:
                gaps.append(AudioGap(after_segment_id=None, duration_ms=max(hole, 0) or None))
        elif chunk.sequence > 0:
            gaps.append(AudioGap(after_segment_id=None, duration_ms=chunk.timestamp_ms or None))
        previous = chunk
    # Segments annoncés mais jamais reçus en fin de session.
    if previous is not None and expected_last is not None and expected_last > previous.sequence:
        gaps.append(AudioGap(after_segment_id=None, duration_ms=None))
    if previous is None and expected_last is not None and expected_last >= 0:
        gaps.append(AudioGap(after_segment_id=None, duration_ms=None))

    for gap in reported or []:
        gaps.append(AudioGap(after_segment_id=None, duration_ms=gap.duration_ms))

    return Coverage(
        received_count=len(ordered),
        last_sequence=last,
        missing_sequences=missing,
        received_duration_ms=sum(c.duration_ms for c in ordered),
        gaps=gaps,
    )
