"""Jeux d'essai audio : manifeste JSON + fichiers WAV (hors dépôt)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


class DatasetNotAllowed(ValueError):
    pass


@dataclass(frozen=True)
class ReferenceSegment:
    role: str
    start_ms: int
    end_ms: int
    text: str


@dataclass(frozen=True)
class DatasetItem:
    audio_id: str
    audio_path: Path
    duration_ms: int
    source_case_id: str | None
    reference_segments: tuple[ReferenceSegment, ...]

    @property
    def reference_text(self) -> str:
        return " ".join(segment.text for segment in self.reference_segments)


@dataclass(frozen=True)
class Dataset:
    name: str
    version: str
    locale: str
    synthetic_only: bool
    consent_documented: bool
    items: tuple[DatasetItem, ...]

    @classmethod
    def load(cls, manifest_path: Path) -> Dataset:
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        root = manifest_path.parent
        dataset = cls(
            name=raw["name"],
            version=raw["version"],
            locale=raw.get("locale", "fr-FR"),
            synthetic_only=bool(raw.get("synthetic_only")),
            consent_documented=bool(raw.get("consent_documented")),
            items=tuple(
                DatasetItem(
                    audio_id=item["audio_id"],
                    audio_path=root / item["audio_file"],
                    duration_ms=int(item["duration_ms"]),
                    source_case_id=item.get("source_case_id"),
                    reference_segments=tuple(
                        ReferenceSegment(**s) for s in item["reference_segments"]
                    ),
                )
                for item in raw["items"]
            ),
        )
        dataset.ensure_allowed()
        return dataset

    def ensure_allowed(self) -> None:
        """Seuls des enregistrements synthétiques ou à consentement documenté quittent Oris."""
        if not (self.synthetic_only or self.consent_documented):
            raise DatasetNotAllowed(
                f"{self.name} : ni synthetic_only ni consent_documented — "
                "envoi à un fournisseur refusé"
            )
