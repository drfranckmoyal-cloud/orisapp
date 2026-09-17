"""Fournisseur « parfait » pour contrôler le banc hors ligne.

Renvoie exactement la référence du jeu d'essai : le banc doit alors donner 100 %
partout. Sert à vérifier jeu, audio et métriques avant tout appel payant.
"""

from __future__ import annotations

from oris_api.benchmark.dataset import Dataset
from oris_api.contracts import TranscriptSegment
from oris_api.domain.types import AudioChunk, GlossaryHint, TranscriptionResult
from oris_api.providers.base import ProviderInfo


class ReferenceProvider:
    info = ProviderInfo(name="reference", version="dataset-truth")

    def __init__(self, dataset: Dataset) -> None:
        self._items = {item.audio_id: item for item in dataset.items}

    async def transcribe(
        self, chunks: list[AudioChunk], locale: str, glossary: list[GlossaryHint]
    ) -> TranscriptionResult:
        item = self._items[chunks[0].session_id]
        segments, labels = [], {}
        for index, ref in enumerate(item.reference_segments):
            segment_id = f"t{index + 1}"
            segments.append(
                TranscriptSegment(
                    segment_id=segment_id,
                    start_ms=ref.start_ms,
                    end_ms=ref.end_ms,
                    speaker_role="unknown",
                    text=ref.text,
                    confidence=1.0,
                    is_final=True,
                )
            )
            labels[segment_id] = ref.role
        return TranscriptionResult(segments, speaker_labels=labels)
