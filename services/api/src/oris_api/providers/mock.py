"""Fournisseurs factices, déterministes, pour le développement et les tests.

Aucun appel réseau. Ils n'inventent rien : hors corpus synthétique, ils renvoient
un résultat vide. Toute sortie passe par la validation de contrat.
"""

from __future__ import annotations

from oris_api.contracts import ClinicalEncounter, TranscriptSegment, validate_contract
from oris_api.contracts.generated import DocumentDocumentType
from oris_api.documents.renderer import (
    DEFAULT_STYLE,
    Style,
    render_consultation_note,
    render_operative_note,
    render_treatment_plan,
)
from oris_api.domain.factual_validator import validate_document
from oris_api.domain.resolver import is_gap_marker
from oris_api.domain.types import (
    AudioChunk,
    AudioGap,
    ExtractionResult,
    GeneratedDocument,
    GlossaryHint,
    TranscriptionResult,
    ValidationIssue,
)
from oris_api.providers.base import ProviderInfo
from oris_api.synthetic.corpus import SYNTHETIC_PAYLOAD_PREFIX, SyntheticCorpus

MOCK_VERSION = "mock-0.2"


class MockSpeechToTextProvider:
    """« Décode » un chunk synthétique `oris-synthetic:<case_id>` en transcript du corpus.

    Un segment `[coupure audio …]` du corpus est restitué comme trou audio.
    """

    info = ProviderInfo(name="mock", version=MOCK_VERSION, capabilities=["synthetic_corpus"])

    def __init__(self, corpus: SyntheticCorpus) -> None:
        self._corpus = corpus

    async def transcribe(
        self, chunks: list[AudioChunk], locale: str, glossary: list[GlossaryHint]
    ) -> TranscriptionResult:
        segments: list[TranscriptSegment] = []
        gaps: list[AudioGap] = []
        for chunk in sorted(chunks, key=lambda c: c.sequence):
            if not chunk.payload.startswith(SYNTHETIC_PAYLOAD_PREFIX):
                continue
            case = self._corpus.get(chunk.payload.removeprefix(SYNTHETIC_PAYLOAD_PREFIX).decode())
            if case is None:
                continue
            previous: str | None = None
            for segment in case.segments:
                validate_contract("TranscriptSegment", segment.model_dump(mode="json"))
                segments.append(segment)
                if is_gap_marker(segment):
                    gaps.append(AudioGap(after_segment_id=previous, duration_ms=None))
                previous = segment.segment_id
        return TranscriptionResult(segments, gaps)


class MockClinicalExtractionProvider:
    """Rejoue l'extraction attendue du corpus pour un transcript reconnu à l'identique."""

    info = ProviderInfo(name="mock", version=MOCK_VERSION, capabilities=["synthetic_corpus"])

    def __init__(self, corpus: SyntheticCorpus) -> None:
        self._corpus = corpus

    async def extract(
        self, segments: list[TranscriptSegment], glossary: list[GlossaryHint]
    ) -> ExtractionResult:
        case = self._corpus.by_transcript(segments)
        if case is None:
            return ExtractionResult(facts=[])
        return ExtractionResult(
            # Le corpus décrit des faits attendus, vérifiés par un humain ; une sortie
            # d'extraction ne l'est jamais.
            facts=[
                f.model_copy(update={"manually_validated": False}, deep=True) for f in case.facts
            ],
            treatment_plan=case.treatment_plan.model_copy(deep=True)
            if case.treatment_plan
            else None,
            procedures=[p.model_copy(deep=True) for p in case.procedures],
        )


class MockDocumentGenerationProvider:
    """Rédaction par gabarits français déterministes (documents/renderer.py)."""

    info = ProviderInfo(name="mock", version=MOCK_VERSION, capabilities=["french_templates"])

    async def generate(
        self,
        encounter: ClinicalEncounter,
        document_type: DocumentDocumentType,
        style: Style | None = None,
    ) -> GeneratedDocument:
        match document_type:
            case "consultation_note":
                return render_consultation_note(encounter, style or DEFAULT_STYLE)
            case "treatment_plan_text":
                return render_treatment_plan(encounter)
            case "operative_note":
                return render_operative_note(encounter)
        raise NotImplementedError(document_type)


class MockClinicalValidationProvider:
    """Délègue au validateur factuel déterministe."""

    info = ProviderInfo(name="mock", version=MOCK_VERSION, capabilities=["factual_validator"])

    async def validate(
        self, document: GeneratedDocument, encounter: ClinicalEncounter
    ) -> list[ValidationIssue]:
        return validate_document(document, encounter)
