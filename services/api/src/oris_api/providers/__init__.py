"""Fournisseurs IA derrière des interfaces : aucun fournisseur codé en dur."""

from oris_api.providers.base import (
    AudioChunk,
    ClinicalExtractionProvider,
    ClinicalValidationProvider,
    DocumentGenerationProvider,
    GeneratedDocument,
    GlossaryHint,
    ProviderInfo,
    SpeechToTextProvider,
    ValidationIssue,
)
from oris_api.providers.factory import ProviderConfigurationError, ProviderSet, build_providers

__all__ = [
    "AudioChunk",
    "ClinicalExtractionProvider",
    "ClinicalValidationProvider",
    "DocumentGenerationProvider",
    "GeneratedDocument",
    "GlossaryHint",
    "ProviderConfigurationError",
    "ProviderInfo",
    "ProviderSet",
    "SpeechToTextProvider",
    "ValidationIssue",
    "build_providers",
]
