"""D'où vient chaque phrase d'un document (spec §30).

Une phrase cite les faits qui l'appuient ; un fait cite les segments réellement
prononcés. La jointure phrase → faits → paroles est faite **ici**, une fois, pour que
le site et l'iPhone montrent exactement la même preuve sans refaire le raisonnement
chacun de son côté — et pour qu'un téléphone n'ait pas à télécharger toute la
transcription pour afficher trois lignes.

Rien n'est inventé au passage : une phrase dont les faits ne citent aucun segment
retrouvable est rendue telle quelle, marquée `sans_preuve`. C'est une information, pas
un défaut à masquer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from oris_api.contracts import ClinicalEncounter, ClinicalFact, TranscriptSegment
from oris_api.db.models import DocumentRow, DocumentVersion, Encounter
from oris_api.ontology.labels import CONCEPTS
from oris_api.services import clinical_store


@dataclass(frozen=True)
class Passage:
    """Une parole de la consultation, telle qu'elle a été transcrite."""

    segment_id: str
    start_ms: int
    speaker_role: str
    text: str


@dataclass(frozen=True)
class FaitAppui:
    """Un fait clinique, dans les mots du praticien plutôt que dans ceux du moteur."""

    fact_id: str
    concept: str
    libelle: str
    valeur: str
    teeth: list[str]
    assertion: str
    clinical_status: str
    certainty: str
    temporality: str
    speaker_role: str
    source_type: str
    manually_validated: bool


@dataclass(frozen=True)
class Alerte:
    code: str
    message: str
    severity: str


@dataclass(frozen=True)
class PhrasePreuve:
    index: int
    section: str
    text: str
    faits: list[FaitAppui] = field(default_factory=list)
    passages: list[Passage] = field(default_factory=list)
    alertes: list[Alerte] = field(default_factory=list)
    #: Aucun passage retrouvé : fait saisi à la main, ou transcription effacée.
    sans_preuve: bool = False
    #: Le fait a été saisi par le praticien : il n'y a pas de parole source à montrer.
    saisi_a_la_main: bool = False


@dataclass(frozen=True)
class PreuveDocument:
    document_id: UUID
    version: int
    object_version: int
    transcription_disponible: bool
    phrases: list[PhrasePreuve]


def _libelle(concept: str) -> str:
    """Le mot français du concept ; à défaut, le concept lui-même, jamais un à-peu-près."""
    label = CONCEPTS.get(concept)
    return label.label if label else concept


def _valeur(fact: ClinicalFact) -> str:
    """La valeur dite, quand c'en est une : un matériau, une demande, un intitulé."""
    return fact.value.strip() if isinstance(fact.value, str) else ""


def _fait(fact: ClinicalFact) -> FaitAppui:
    return FaitAppui(
        fact_id=fact.fact_id,
        concept=fact.concept,
        libelle=_libelle(fact.concept),
        valeur=_valeur(fact),
        teeth=list(fact.teeth),
        assertion=fact.assertion,
        clinical_status=fact.clinical_status,
        certainty=fact.certainty,
        temporality=fact.temporality,
        speaker_role=fact.speaker_role,
        source_type=fact.source_type,
        manually_validated=fact.manually_validated,
    )


def construire(
    obj: ClinicalEncounter,
    segments: list[TranscriptSegment],
    claims: list[dict[str, Any]],
    document_id: UUID,
    version: int,
    object_version: int,
) -> PreuveDocument:
    """La preuve, phrase par phrase, dans l'ordre du document."""
    par_fait = {fact.fact_id: fact for fact in obj.facts}
    par_segment = {segment.segment_id: segment for segment in segments}
    alertes = {warning.code: warning for warning in obj.warnings}
    phrases: list[PhrasePreuve] = []

    for index, claim in enumerate(claims):
        faits = [par_fait[fid] for fid in claim.get("fact_ids", []) if fid in par_fait]
        # Un segment cité deux fois par deux faits ne s'affiche qu'une fois, dans
        # l'ordre où il a été prononcé.
        vus: dict[str, TranscriptSegment] = {}
        for fact in faits:
            for segment_id in fact.evidence_segment_ids:
                segment = par_segment.get(segment_id)
                if segment is not None:
                    vus.setdefault(segment_id, segment)
        passages = [
            Passage(
                segment_id=segment.segment_id,
                start_ms=segment.start_ms,
                speaker_role=segment.speaker_role,
                text=segment.text,
            )
            for segment in sorted(vus.values(), key=lambda s: s.start_ms)
        ]
        phrases.append(
            PhrasePreuve(
                index=index,
                section=claim.get("section", ""),
                text=claim.get("text", ""),
                faits=[_fait(fact) for fact in faits],
                passages=passages,
                alertes=[
                    Alerte(
                        code=alertes[code].code,
                        message=alertes[code].message,
                        severity=alertes[code].severity,
                    )
                    for code in claim.get("warning_codes", [])
                    if code in alertes
                ],
                sans_preuve=not passages,
                saisi_a_la_main=bool(faits) and all(f.source_type == "manual" for f in faits),
            )
        )

    return PreuveDocument(
        document_id=document_id,
        version=version,
        object_version=object_version,
        transcription_disponible=bool(segments),
        phrases=phrases,
    )


def pour_document(
    session: Session, encounter: Encounter, document: DocumentRow, version: DocumentVersion
) -> PreuveDocument:
    """Charge l'objet clinique **de l'époque du document** et la transcription gardée."""
    obj = clinical_store.load_version(
        session, encounter.id, version.generated_from_object_version
    ) or clinical_store.load_current(session, encounter)
    return construire(
        obj=obj,
        segments=clinical_store.load_segments(session, encounter.id),
        claims=list(version.claims),
        document_id=document.id,
        version=version.version,
        object_version=version.generated_from_object_version,
    )
