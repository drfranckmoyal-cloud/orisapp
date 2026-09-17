"""Types d'échange entre les étapes du pipeline clinique."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from oris_api.contracts import ClinicalFact, Procedure, TranscriptSegment, TreatmentPlan
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
class AudioGap:
    """Portion de consultation non captée. `duration_ms` None = durée inconnue."""

    after_segment_id: str | None
    duration_ms: int | None


@dataclass(frozen=True)
class TranscriptionResult:
    segments: list[TranscriptSegment]
    gaps: list[AudioGap] = field(default_factory=list)
    # Étiquette brute du locuteur par segment (« 0 », « Guest-1 ») avant attribution des rôles.
    speaker_labels: dict[str, str] = field(default_factory=dict)
    # Identifiants techniques du fournisseur (requête, modèle) ; jamais de contenu.
    provider_request_id: str | None = None


@dataclass(frozen=True)
class ExtractionResult:
    facts: list[ClinicalFact]
    treatment_plan: TreatmentPlan | None = None
    procedures: list[Procedure] = field(default_factory=list)


@dataclass(frozen=True)
class Claim:
    """Une phrase de document et ce qui l'appuie : faits et/ou alertes."""

    section: str
    text: str
    fact_ids: tuple[str, ...] = ()
    warning_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class GeneratedDocument:
    document_type: DocumentDocumentType
    content: str
    claims: tuple[Claim, ...]

    @property
    def supported_fact_ids(self) -> list[str]:
        seen: dict[str, None] = {}
        for claim in self.claims:
            for fact_id in claim.fact_ids:
                seen.setdefault(fact_id, None)
        return list(seen)


IssueCode = Literal[
    "unknown_fact_id",
    "unsupported_claim",
    "tooth_not_supported",
    "performed_not_supported",
    "fact_not_rendered",
    "unrendered_concept",
]


@dataclass(frozen=True)
class ValidationIssue:
    code: IssueCode
    severity: Literal["review", "critical"]
    fact_id: str | None = None
    claim_index: int | None = None
