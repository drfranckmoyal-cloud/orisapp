"""Configuration par environnement (spec §85–86).

Les fournisseurs IA sont de la configuration, jamais de la logique métier.
STT : `mock`, `azure_speech` ou `deepgram` (banc d'essai M4, aucun choisi par défaut).
Extraction, rédaction, validation : `mock` jusqu'à M5.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

AppEnv = Literal["local", "test", "staging", "production"]
ProviderName = Literal["mock"]
SttProviderName = Literal["mock", "azure_speech", "deepgram"]
ExtractionProviderName = Literal["mock", "anthropic"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: AppEnv = "local"
    database_url: str = "postgresql://oris:oris@localhost:5432/oris"
    redis_url: str | None = None

    stt_provider: SttProviderName = "mock"
    # Envoyer de l'audio à un service extérieur exige un accord explicite (spec §66).
    allow_external_stt: bool = False
    stt_use_glossary: bool = True
    azure_speech_key: SecretStr | None = None
    azure_speech_endpoint: str | None = None  # https://<ressource>.cognitiveservices.azure.com
    deepgram_api_key: SecretStr | None = None
    deepgram_base_url: str = "https://api.deepgram.com"
    clinical_extraction_provider: ExtractionProviderName = "mock"
    # Envoyer le transcript à un modèle extérieur exige un accord explicite (spec §66).
    allow_external_llm: bool = False
    anthropic_api_key: SecretStr | None = None
    anthropic_model: str = "claude-sonnet-5"
    document_generation_provider: ProviderName = "mock"
    clinical_validation_provider: ProviderName = "mock"

    audio_retention_mode: Literal["ephemeral"] = "ephemeral"
    # Stockage transitoire des segments audio : `memory` (tests) ou `local_temp` (dev).
    audio_sink: Literal["memory", "local_temp"] = "local_temp"
    audio_temp_dir: Path = Path.home() / "Library" / "Caches" / "Oris" / "audio"
    audio_max_chunk_bytes: int = 256_000
    # Pièces jointes du patient : photos, radios, empreintes (spec §55). **Pas dans
    # `Caches`** : macOS s'autorise à vider ce dossier quand il manque de place, et il
    # n'est pas sauvegardé comme le reste. L'audio, lui, y reste — il est éphémère par
    # décision (D010) ; une radio ne l'est pas.
    attachment_dir: Path = Path.home() / "Library" / "Application Support" / "Oris" / "attachments"
    # Connecteur SmileCloud : éteint tant qu'il n'est pas construit.
    smilecloud_enabled: bool = False

    # Agenda du jour (écran « Votre journée »). Oris ne va rien chercher : l'extension
    # Chrome lui **dépose** la journée. Rangée hors de la base clinique, un fichier par
    # date : ce sont de vrais noms, ils n'entrent dans le dossier clinique que le jour
    # où le praticien crée le dossier lui-même.
    journee_dir: Path = Path.home() / "Library" / "Application Support" / "Oris" / "journees"
    # Secret partagé, facultatif : renseigné, le dépôt l'exige en `Authorization: Bearer`.
    # Le dépôt n'accepte de toute façon que les appels venus de cette machine.
    journee_depot_token: SecretStr | None = None
    max_session_minutes: int = 90
    warn_session_minutes: int = 80

    # Information du patient avant l'écoute (§65) : paramètre, pas interprétation juridique.
    patient_information_mode: Literal["none", "confirm"] = "confirm"

    # Feature flags (spec §85).
    enable_live_transcript: bool = False
    enable_operative_generation: bool = True
    enable_voice_correction: bool = False
    enable_attachments: bool = False
    enable_advanced_warnings: bool = False

    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    @field_validator(
        "azure_speech_key",
        "azure_speech_endpoint",
        "deepgram_api_key",
        "anthropic_api_key",
        "journee_depot_token",
        mode="before",
    )
    @classmethod
    def empty_means_missing(cls, value: object) -> object:
        """Une clé laissée vide dans .env est une clé absente."""
        return None if isinstance(value, str) and not value.strip() else value

    @field_validator("database_url")
    @classmethod
    def use_psycopg_driver(cls, url: str) -> str:
        """`postgresql://` (format de .env.example) -> pilote psycopg 3 pour SQLAlchemy."""
        if url.startswith("postgresql://"):
            return "postgresql+psycopg://" + url.removeprefix("postgresql://")
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()
