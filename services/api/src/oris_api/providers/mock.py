"""Fournisseurs factices, déterministes, pour le développement et les tests.

Ils ne font aucun appel réseau et n'inventent rien : sans script, ils renvoient
un résultat vide. Toute sortie passe par la validation de contrat.
"""

from __future__ import annotations

from oris_api.contracts import (
    ClinicalEncounter,
    ClinicalFact,
    TranscriptSegment,
    validate_contract,
)
from oris_api.contracts.generated import DocumentDocumentType
from oris_api.providers.base import (
    AudioChunk,
    GeneratedDocument,
    GlossaryHint,
    ProviderInfo,
    ValidationIssue,
)

MOCK_VERSION = "mock-0.1"


class MockSpeechToTextProvider:
    """Renvoie un transcript synthétique scripté, quel que soit l'audio reçu."""

    info = ProviderInfo(name="mock", version=MOCK_VERSION, capabilities=["scripted_transcript"])

    def __init__(self, scripted_segments: list[TranscriptSegment] | None = None) -> None:
        self._segments = list(scripted_segments or [])

    async def transcribe(
        self, chunks: list[AudioChunk], locale: str, glossary: list[GlossaryHint]
    ) -> list[TranscriptSegment]:
        for segment in self._segments:
            validate_contract("TranscriptSegment", segment.model_dump(mode="json"))
        return list(self._segments)


class MockClinicalExtractionProvider:
    """Renvoie des faits scriptés, filtrés aux segments effectivement fournis."""

    info = ProviderInfo(name="mock", version=MOCK_VERSION, capabilities=["scripted_facts"])

    def __init__(self, scripted_facts: list[ClinicalFact] | None = None) -> None:
        self._facts = list(scripted_facts or [])

    async def extract(
        self, segments: list[TranscriptSegment], glossary: list[GlossaryHint]
    ) -> list[ClinicalFact]:
        available = {segment.segment_id for segment in segments}
        facts = []
        for fact in self._facts:
            validate_contract("ClinicalFact", fact.model_dump(mode="json"))
            # Un fait audio sans preuve présente dans ce transcript n'est pas émis.
            if fact.source_type == "audio" and not set(fact.evidence_segment_ids) <= available:
                continue
            facts.append(fact)
        return facts


class MockDocumentGenerationProvider:
    """Projection littérale des faits : une ligne par fait, sans reformulation."""

    info = ProviderInfo(name="mock", version=MOCK_VERSION, capabilities=["literal_projection"])

    async def generate(
        self, encounter: ClinicalEncounter, document_type: DocumentDocumentType
    ) -> GeneratedDocument:
        lines = []
        for fact in encounter.facts:
            teeth = f" [{', '.join(fact.teeth)}]" if fact.teeth else ""
            lines.append(
                f"- {fact.concept}{teeth} : {fact.value} "
                f"({fact.assertion}, {fact.clinical_status}, {fact.certainty})"
            )
        return GeneratedDocument(
            document_type=document_type,
            content="\n".join(lines),
            supported_fact_ids=[fact.fact_id for fact in encounter.facts],
        )


class MockClinicalValidationProvider:
    """Contrôle déterministe : chaque fait cité par le document doit exister."""

    info = ProviderInfo(name="mock", version=MOCK_VERSION, capabilities=["fact_id_support"])

    async def validate(
        self, document: GeneratedDocument, encounter: ClinicalEncounter
    ) -> list[ValidationIssue]:
        known = {fact.fact_id for fact in encounter.facts}
        issues = [
            ValidationIssue(code="unknown_fact_id", severity="critical", fact_id=fact_id)
            for fact_id in document.supported_fact_ids
            if fact_id not in known
        ]
        if document.content.strip() and not document.supported_fact_ids:
            issues.append(ValidationIssue(code="empty_support", severity="critical"))
        return issues
