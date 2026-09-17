"""Sélection des fournisseurs selon la configuration."""

from __future__ import annotations

from dataclasses import dataclass

from oris_api.config import Settings
from oris_api.providers.base import (
    ClinicalExtractionProvider,
    ClinicalValidationProvider,
    DocumentGenerationProvider,
    SpeechToTextProvider,
)
from oris_api.providers.mock import (
    MockClinicalExtractionProvider,
    MockClinicalValidationProvider,
    MockDocumentGenerationProvider,
    MockSpeechToTextProvider,
)
from oris_api.synthetic.corpus import SyntheticCorpus, default_corpus


class ProviderConfigurationError(RuntimeError):
    pass


@dataclass(frozen=True)
class ProviderSet:
    speech_to_text: SpeechToTextProvider
    clinical_extraction: ClinicalExtractionProvider
    document_generation: DocumentGenerationProvider
    clinical_validation: ClinicalValidationProvider


def build_providers(settings: Settings, corpus: SyntheticCorpus | None = None) -> ProviderSet:
    configured = {
        "STT_PROVIDER": settings.stt_provider,
        "CLINICAL_EXTRACTION_PROVIDER": settings.clinical_extraction_provider,
        "DOCUMENT_GENERATION_PROVIDER": settings.document_generation_provider,
        "CLINICAL_VALIDATION_PROVIDER": settings.clinical_validation_provider,
    }
    for variable, name in configured.items():
        if name != "mock":
            raise ProviderConfigurationError(f"{variable}: fournisseur « {name} » non disponible")
    corpus = corpus or (default_corpus() if settings.app_env in {"local", "test"} else None)
    if corpus is None:
        corpus = SyntheticCorpus([])
    return ProviderSet(
        speech_to_text=MockSpeechToTextProvider(corpus),
        clinical_extraction=MockClinicalExtractionProvider(corpus),
        document_generation=MockDocumentGenerationProvider(),
        clinical_validation=MockClinicalValidationProvider(),
    )
