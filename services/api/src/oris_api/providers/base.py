"""Interfaces des fournisseurs IA (spec §26, docs/AI_ARCHITECTURE.md).

La logique métier ne dépend que de ces interfaces. Un fournisseur réel (STT,
LLM) est un adaptateur choisi par configuration, après benchmark (D019, D020).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol, runtime_checkable

from oris_api.contracts import ClinicalEncounter, ClinicalFact, TranscriptSegment
from oris_api.contracts.generated import DocumentDocumentType


@dataclass(frozen=True)
class AudioChunk:
    session_id: str
    sequence: int
    timestamp_ms: int
    checksum: str
    payload: bytes


@dataclass(frozen=True)
class GlossaryHint:
    heard: str
    canonical: str


@dataclass(frozen=True)
class GeneratedDocument:
    document_type: DocumentDocumentType
    content: str
    supported_fact_ids: list[str]


@dataclass(frozen=True)
class ValidationIssue:
    code: Literal["unknown_fact_id", "unsupported_document", "empty_support"]
    severity: Literal["review", "critical"]
    fact_id: str | None = None


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
    ) -> list[TranscriptSegment]: ...


@runtime_checkable
class ClinicalExtractionProvider(Protocol):
    info: ProviderInfo

    async def extract(
        self, segments: list[TranscriptSegment], glossary: list[GlossaryHint]
    ) -> list[ClinicalFact]:
        """Candidats de faits. Ne doit jamais produire un fait sans segment source."""
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
