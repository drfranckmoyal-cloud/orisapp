"""Configuration par environnement (spec §85–86).

Les fournisseurs IA sont de la configuration, jamais de la logique métier.
Tant que le Milestone M5 n'est pas atteint, seul `mock` est accepté.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

AppEnv = Literal["local", "test", "staging", "production"]
ProviderName = Literal["mock"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: AppEnv = "local"
    database_url: str = "postgresql://oris:oris@localhost:5432/oris"
    redis_url: str | None = None

    stt_provider: ProviderName = "mock"
    clinical_extraction_provider: ProviderName = "mock"
    document_generation_provider: ProviderName = "mock"
    clinical_validation_provider: ProviderName = "mock"

    audio_retention_mode: Literal["ephemeral"] = "ephemeral"
    # Stockage transitoire des segments audio : `memory` (tests) ou `local_temp` (dev).
    audio_sink: Literal["memory", "local_temp"] = "local_temp"
    audio_temp_dir: Path = Path.home() / "Library" / "Caches" / "Oris" / "audio"
    audio_max_chunk_bytes: int = 256_000
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
