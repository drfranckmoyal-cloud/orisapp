"""Fournisseurs IA derrière des interfaces : aucun fournisseur codé en dur."""

from oris_api.domain.types import (
    AudioChunk,
    ExtractionResult,
    GeneratedDocument,
    GlossaryHint,
    TranscriptionResult,
    ValidationIssue,
)
from oris_api.providers.base import (
    ClinicalExtractionProvider,
    ClinicalValidationProvider,
    DocumentGenerationProvider,
    ProviderInfo,
    SpeechToTextProvider,
)
from oris_api.providers.factory import ProviderConfigurationError, ProviderSet, build_providers

__all__ = [
    "AudioChunk",
    "ClinicalExtractionProvider",
    "ClinicalValidationProvider",
    "DocumentGenerationProvider",
    "ExtractionResult",
    "GeneratedDocument",
    "GlossaryHint",
    "ProviderConfigurationError",
    "ProviderInfo",
    "ProviderSet",
    "SpeechToTextProvider",
    "TranscriptionResult",
    "ValidationIssue",
    "build_providers",
]
