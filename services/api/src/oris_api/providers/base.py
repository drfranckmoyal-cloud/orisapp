"""Interfaces des fournisseurs IA (spec §26, docs/AI_ARCHITECTURE.md).

La logique métier ne dépend que de ces interfaces. Un fournisseur réel (STT,
LLM) est un adaptateur choisi par configuration, après benchmark (D019, D020).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Literal, Protocol, runtime_checkable

from oris_api.contracts import ClinicalEncounter, TranscriptSegment
from oris_api.contracts.generated import DocumentDocumentType
from oris_api.domain.types import (
    AudioChunk,
    ExtractionResult,
    GeneratedDocument,
    GlossaryHint,
    TranscriptionResult,
    ValidationIssue,
)


@dataclass(frozen=True)
class ProviderInfo:
    name: str
    version: str
    capabilities: list[str] = field(default_factory=list)


@runtime_checkable
class SpeechToTextProvider(Protocol):
    info: ProviderInfo

    async def transcribe(
        self, chunks: list[AudioChunk], locale: str, glossary: list[GlossaryHint]
    ) -> TranscriptionResult:
        """Segments finaux et trous audio non récupérés, jamais masqués."""
        ...


class TranscriptionUnavailable(RuntimeError):
    """Échec temporaire du fournisseur (réseau, quota, panne) : l'audio est conservé.

    `code` est un code technique stable ; jamais de contenu audio ni de texte.
    """

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class ExtractionUnavailable(RuntimeError):
    """Extraction impossible : panne du fournisseur, ou sortie refusée après un essai."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class StreamEvent:
    """Résultat temps réel. `audio_end_ms` : fin de la parole reconnue dans l'audio."""

    kind: Literal["interim", "final", "gap", "reconnected"]
    segment: TranscriptSegment | None
    speaker_label: str | None
    audio_end_ms: int
    received_monotonic: float


@runtime_checkable
class StreamingSpeechToTextProvider(Protocol):
    info: ProviderInfo

    def stream(
        self, chunks: AsyncIterator[AudioChunk], locale: str, glossary: list[GlossaryHint]
    ) -> AsyncIterator[StreamEvent]:
        """Transcription progressive. Un trou (reconnexion) est émis, jamais masqué."""
        ...


@runtime_checkable
class ClinicalExtractionProvider(Protocol):
    info: ProviderInfo

    async def extract(
        self, segments: list[TranscriptSegment], glossary: list[GlossaryHint]
    ) -> ExtractionResult:
        """Candidats de faits, plan et actes. Ne doit rien produire sans segment source."""
        ...


@runtime_checkable
class DocumentGenerationProvider(Protocol):
    info: ProviderInfo

    async def generate(
        self, encounter: ClinicalEncounter, document_type: DocumentDocumentType
    ) -> GeneratedDocument:
        """Entrée : l'objet clinique uniquement, jamais le transcript (D008)."""
        ...


@runtime_checkable
class ClinicalValidationProvider(Protocol):
    info: ProviderInfo

    async def validate(
        self, document: GeneratedDocument, encounter: ClinicalEncounter
    ) -> list[ValidationIssue]:
        """Vérifie un document contre les faits. Ne peut ajouter aucun fait."""
        ...
