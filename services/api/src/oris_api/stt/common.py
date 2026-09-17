"""Outils partagés par les adaptateurs STT."""

from __future__ import annotations

from oris_api.contracts import TranscriptSegment
from oris_api.domain.types import GlossaryHint
from oris_api.ontology.stt_glossary import DENTAL_GLOSSARY_FR


def glossary_terms(glossary: list[GlossaryHint], limit: int = 50) -> list[str]:
    """Termes à pousser au fournisseur : glossaire du praticien, puis glossaire dentaire."""
    terms: dict[str, None] = {}
    for hint in glossary:
        terms.setdefault(hint.canonical, None)
    for term in DENTAL_GLOSSARY_FR:
        terms.setdefault(term, None)
    return list(terms)[:limit]


def segment(
    index: int, start_ms: int, end_ms: int, text: str, confidence: float | None
) -> TranscriptSegment:
    return TranscriptSegment(
        segment_id=f"t{index + 1}",
        start_ms=max(0, start_ms),
        end_ms=max(start_ms, end_ms),
        speaker_role="unknown",  # rôle attribué ensuite (domain/speaker_roles.py)
        text=text.strip(),
        confidence=min(1.0, max(0.0, confidence if confidence is not None else 0.0)),
        is_final=True,
    )
