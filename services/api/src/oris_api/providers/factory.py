"""Sélection des fournisseurs selon la configuration."""

from __future__ import annotations

from dataclasses import dataclass

from oris_api.config import Settings
from oris_api.llm.anthropic_extraction import AnthropicExtractionProvider
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
from oris_api.stt.azure_speech import AzureFastTranscriptionProvider
from oris_api.stt.deepgram import DeepgramPrerecordedProvider
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
        speech_to_text=build_speech_to_text(settings, corpus),
        clinical_extraction=build_clinical_extraction(settings, corpus),
        document_generation=MockDocumentGenerationProvider(),
        clinical_validation=MockClinicalValidationProvider(),
    )


def build_speech_to_text(settings: Settings, corpus: SyntheticCorpus) -> SpeechToTextProvider:
    if settings.stt_provider == "mock":
        return MockSpeechToTextProvider(corpus)
    if not settings.allow_external_stt:
        raise ProviderConfigurationError(
            "STT_PROVIDER externe refusé : ALLOW_EXTERNAL_STT=true requis (envoi d'audio hors Oris)"
        )
    if settings.stt_provider == "deepgram":
        if settings.deepgram_api_key is None:
            raise ProviderConfigurationError("DEEPGRAM_API_KEY manquante")
        return DeepgramPrerecordedProvider(
            settings.deepgram_api_key.get_secret_value(),
            settings.deepgram_base_url,
            use_glossary=settings.stt_use_glossary,
        )
    if settings.azure_speech_key is None or not settings.azure_speech_endpoint:
        raise ProviderConfigurationError("AZURE_SPEECH_KEY ou AZURE_SPEECH_ENDPOINT manquante")
    return AzureFastTranscriptionProvider(
        settings.azure_speech_key.get_secret_value(),
        settings.azure_speech_endpoint,
        use_glossary=settings.stt_use_glossary,
    )


def build_clinical_extraction(
    settings: Settings, corpus: SyntheticCorpus
) -> ClinicalExtractionProvider:
    """Extraction clinique : mock par défaut ; un modèle externe exige un accord explicite."""
    if settings.clinical_extraction_provider == "mock":
        return MockClinicalExtractionProvider(corpus)
    if not settings.allow_external_llm:
        raise ProviderConfigurationError(
            "CLINICAL_EXTRACTION_PROVIDER externe refusé : ALLOW_EXTERNAL_LLM=true requis "
            "(envoi du transcript hors Oris)"
        )
    if settings.anthropic_api_key is None:
        raise ProviderConfigurationError("ANTHROPIC_API_KEY manquante")
    return AnthropicExtractionProvider(
        settings.anthropic_api_key.get_secret_value(), settings.anthropic_model
    )
