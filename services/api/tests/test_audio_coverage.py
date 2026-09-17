"""Calcul de couverture audio : aucun trou n'est jamais masqué."""

from __future__ import annotations

from oris_api.domain.audio_coverage import ChunkInfo, ReportedGap, compute_coverage


def contiguous(count: int, duration: int = 2000) -> list[ChunkInfo]:
    return [ChunkInfo(i, i * duration, duration) for i in range(count)]


def test_contiguous_chunks_are_complete() -> None:
    result = compute_coverage(contiguous(5), final_sequence=4)
    assert result.complete
    assert result.received_duration_ms == 10_000
    assert result.last_sequence == 4


def test_empty_session_without_announcement_is_complete() -> None:
    assert compute_coverage([]).complete


def test_missing_middle_chunk_is_a_gap() -> None:
    chunks = [c for c in contiguous(5) if c.sequence != 2]
    result = compute_coverage(chunks, final_sequence=4)
    assert result.missing_sequences == [2]
    assert [g.duration_ms for g in result.gaps] == [2000]


def test_missing_trailing_chunks_are_a_gap() -> None:
    result = compute_coverage(contiguous(3), final_sequence=5)
    assert result.missing_sequences == [3, 4, 5]
    assert len(result.gaps) == 1


def test_missing_first_chunk_is_a_gap() -> None:
    chunks = contiguous(3)[1:]
    result = compute_coverage(chunks, final_sequence=2)
    assert result.missing_sequences == [0]
    assert [g.duration_ms for g in result.gaps] == [2000]


def test_timestamp_discontinuity_without_missing_sequence_is_a_gap() -> None:
    chunks = [ChunkInfo(0, 0, 2000), ChunkInfo(1, 2000, 2000), ChunkInfo(2, 124_000, 2000)]
    result = compute_coverage(chunks, final_sequence=2)
    assert result.missing_sequences == []
    assert [g.duration_ms for g in result.gaps] == [120_000]  # test J : 2 minutes


def test_small_rounding_jitter_is_tolerated() -> None:
    chunks = [ChunkInfo(0, 0, 1999), ChunkInfo(1, 2000, 2000)]
    assert compute_coverage(chunks, final_sequence=1).complete


def test_announced_audio_never_received_is_a_gap() -> None:
    result = compute_coverage([], final_sequence=3)
    assert result.missing_sequences == [0, 1, 2, 3]
    assert len(result.gaps) == 1


def test_reported_interruptions_are_gaps() -> None:
    result = compute_coverage(
        contiguous(2), final_sequence=1, reported=[ReportedGap("microphone_lost", 30_000)]
    )
    assert [g.duration_ms for g in result.gaps] == [30_000]
