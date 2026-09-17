"""Interfaces des fournisseurs IA (spec §26, docs/AI_ARCHITECTURE.md).

La logique métier ne dépend que de ces interfaces. Un fournisseur réel (STT,
LLM) est un adaptateur choisi par configuration, après benchmark (D019, D020).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

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
