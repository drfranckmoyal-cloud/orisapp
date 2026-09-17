"""Résolveur clinique déterministe (docs/AI_ARCHITECTURE.md §4, spec §25 étape 4).

Contrôle la cohérence d'une sortie d'extraction avant qu'elle ne devienne l'objet
clinique. Il ne corrige rien : une violation rejette la sortie entière
(ACCEPTANCE_CRITERIA : « invalid provider output retried or rejected, never
silently coerced »). Les violations ne citent que des identifiants.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from oris_api.contracts import ClinicalFact, Procedure, TranscriptSegment, TreatmentPlan

GAP_MARKER = re.compile(r"^\s*\[coupure audio[^\]]*\]\s*$", re.IGNORECASE)

# Statuts qui supposent un constat ou un jugement du praticien (spec §19.3, test H).
CLINICIAN_ONLY_STATUSES = frozenset(
    {"observed", "clinician_assessment", "differential", "performed"}
)
CLINICIAN_ONLY_CATEGORIES = frozenset({"clinical_finding", "radiographic_finding", "diagnosis"})
EVIDENCE_REQUIRED_SOURCES = frozenset({"audio", "system_test"})

# Statut d'un élément de plan -> statut de fait qui doit l'appuyer.
PLAN_STATUS_TO_FACT_STATUS = {
    "discussed": "discussed",
    "proposed": "proposed",
    "accepted": "accepted",
    "refused": "refused",
    "deferred": "deferred",
    "planned": "planned",
    "completed": "performed",
}
PROCEDURE_STATUS_TO_FACT_STATUS = {"performed": "performed", "planned": "planned"}


@dataclass(frozen=True)
class Violation:
    rule: str
    subject_id: str


def is_gap_marker(segment: TranscriptSegment) -> bool:
    return bool(GAP_MARKER.match(segment.text))


def check_facts(facts: list[ClinicalFact], segments: list[TranscriptSegment]) -> list[Violation]:
    violations: list[Violation] = []
    segment_ids = {s.segment_id for s in segments}
    gap_ids = {s.segment_id for s in segments if is_gap_marker(s)}
    seen: set[str] = set()

    for fact in facts:
        fid = fact.fact_id
        if fid in seen:
            violations.append(Violation("DUPLICATE_FACT_ID", fid))
        seen.add(fid)

        evidence = set(fact.evidence_segment_ids)
        if fact.source_type in EVIDENCE_REQUIRED_SOURCES:
            if not evidence:
                violations.append(Violation("EVIDENCE_MISSING", fid))
            elif not evidence <= segment_ids:
                violations.append(Violation("EVIDENCE_UNKNOWN", fid))
            elif evidence <= gap_ids:
                violations.append(Violation("EVIDENCE_IS_AUDIO_GAP", fid))

        # Test G : un acte futur n'est jamais réalisé.
        if fact.clinical_status == "performed" and fact.temporality == "future":
            violations.append(Violation("PERFORMED_IN_FUTURE", fid))

        # Test H : la parole du patient ne devient pas un constat ou un diagnostic.
        if fact.speaker_role == "patient" and (
            fact.clinical_status in CLINICIAN_ONLY_STATUSES
            or fact.category in CLINICIAN_ONLY_CATEGORIES
        ):
            violations.append(Violation("PATIENT_PROMOTED_TO_CLINICIAN", fid))

        # Test C : « peut-être » ne devient pas certain.
        if fact.assertion == "uncertain" and fact.certainty == "certain":
            violations.append(Violation("UNCERTAINTY_LOST", fid))

    return violations


def check_plan(plan: TreatmentPlan | None, facts: list[ClinicalFact]) -> list[Violation]:
    if plan is None:
        return []
    violations: list[Violation] = []
    by_id = {f.fact_id: f for f in facts}
    for item in plan.items:
        iid = item.item_id
        if not item.evidence_fact_ids:
            violations.append(Violation("PLAN_ITEM_WITHOUT_EVIDENCE", iid))
            continue
        if not set(item.evidence_fact_ids) <= by_id.keys():
            violations.append(Violation("PLAN_EVIDENCE_UNKNOWN", iid))
            continue
        evidence = [by_id[i] for i in item.evidence_fact_ids]
        # Test E : une option ne devient acceptée que si un fait l'accepte.
        if PLAN_STATUS_TO_FACT_STATUS[item.status] not in {f.clinical_status for f in evidence}:
            violations.append(Violation("PLAN_STATUS_UNSUPPORTED", iid))
        supported_teeth = {tooth for f in evidence for tooth in f.teeth}
        if not set(item.teeth) <= supported_teeth:
            violations.append(Violation("PLAN_TEETH_UNSUPPORTED", iid))
    return violations


def check_procedures(procedures: list[Procedure], facts: list[ClinicalFact]) -> list[Violation]:
    violations: list[Violation] = []
    by_id = {f.fact_id: f for f in facts}
    for procedure in procedures:
        pid = procedure.procedure_id
        if not procedure.evidence_fact_ids or not set(procedure.evidence_fact_ids) <= by_id.keys():
            violations.append(Violation("PROCEDURE_EVIDENCE_UNKNOWN", pid))
            continue
        evidence = [by_id[i] for i in procedure.evidence_fact_ids]
        required = PROCEDURE_STATUS_TO_FACT_STATUS.get(procedure.status)
        if required and required not in {f.clinical_status for f in evidence}:
            violations.append(Violation("PROCEDURE_STATUS_UNSUPPORTED", pid))
        # Spec §20 / test « matériau habituel non prononcé » : toute valeur textuelle
        # d'un emplacement opératoire doit avoir été dite, donc portée par un fait :
        # soit la même valeur, soit un fait dont le concept nomme l'emplacement.
        # (Correspondance emplacement -> concept explicite prévue avec les gabarits M7.)
        spoken_values = {f.value for f in evidence if isinstance(f.value, str)}
        for slot, value in procedure.structured_data.items():
            named = any(slot in f.concept for f in evidence)
            if isinstance(value, str) and value not in spoken_values and not named:
                violations.append(Violation("PROCEDURE_DATA_UNSUPPORTED", pid))
                break
    return violations


def resolve(
    facts: list[ClinicalFact],
    plan: TreatmentPlan | None,
    procedures: list[Procedure],
    segments: list[TranscriptSegment],
) -> list[Violation]:
    """Toutes les violations ; liste vide = sortie acceptable."""
    return (
        check_facts(facts, segments) + check_plan(plan, facts) + check_procedures(procedures, facts)
    )
