"""Résolveur clinique déterministe (docs/AI_ARCHITECTURE.md §4, spec §25 étape 4).

Contrôle la cohérence d'une sortie d'extraction avant qu'elle ne devienne l'objet
clinique. Il ne corrige rien : une violation rejette la sortie entière
(ACCEPTANCE_CRITERIA : « invalid provider output retried or rejected, never
silently coerced »). Les violations ne citent que des identifiants.
"""

from __future__ import annotations

import re
import unicodedata
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


def check_facts(
    facts: list[ClinicalFact], segments: list[TranscriptSegment], from_extraction: bool = False
) -> list[Violation]:
    violations: list[Violation] = []
    segment_ids = {s.segment_id for s in segments}
    gap_ids = {s.segment_id for s in segments if is_gap_marker(s)}
    seen: set[str] = set()

    for fact in facts:
        fid = fact.fact_id
        if fid in seen:
            violations.append(Violation("DUPLICATE_FACT_ID", fid))
        seen.add(fid)

        # Invariant 9 : seul le praticien valide ; un fournisseur ne peut pas le prétendre.
        if from_extraction and fact.manually_validated:
            violations.append(Violation("EXTRACTION_SELF_VALIDATED", fid))

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


def check_procedures(
    procedures: list[Procedure],
    facts: list[ClinicalFact],
    segments: list[TranscriptSegment] | None = None,
) -> list[Violation]:
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
        # Spec §20 / test « matériau habituel non prononcé » : toute valeur textuelle d'un
        # emplacement opératoire doit avoir été **prononcée** — dans la valeur d'un fait
        # d'appui, dans le nom d'un concept d'appui, ou dans les paroles de la consultation.
        if donnees_non_dites(procedure, evidence, segments or []):
            violations.append(Violation("PROCEDURE_DATA_UNSUPPORTED", pid))
    return violations


def _normaliser(texte: str) -> str:
    """Pour comparer ce qui est écrit à ce qui a été dit : minuscules, sans accents ni
    ponctuation, « % » lu « pour cent ». « Articaïne 4 % » et « articaine à 4 pour cent »
    disent la même chose ; une comparaison à la lettre refusait la consultation entière
    (compte rendu opératoire, 13/11/2026)."""
    texte = unicodedata.normalize("NFKD", texte.lower())
    texte = "".join(c for c in texte if not unicodedata.combining(c))
    texte = texte.replace("%", " pour cent ")
    return " ".join(re.sub(r"[^0-9a-z]+", " ", texte).split())


def _dit(valeur: str, texte: str, mots: set[str]) -> bool:
    """La valeur figure-t-elle dans les paroles ? Telle quelle, ou mot pour mot : chacun
    de ses mots porteurs (nombres, et mots de trois lettres ou plus) a été prononcé."""
    v = _normaliser(valeur)
    if not v or f" {v} " in f" {texte} ":
        return True
    porteurs = [m for m in v.split() if len(m) >= 3 or m.isdigit()]
    return bool(porteurs) and all(m in mots for m in porteurs)


def donnees_non_dites(
    procedure: Procedure, evidence: list[ClinicalFact], segments: list[TranscriptSegment]
) -> list[str]:
    """Les emplacements de l'acte dont la valeur n'a été ni dite ni nommée par un fait.

    Les paroles comptées sont celles de toute la consultation : une précision technique
    (« articaïne », « fil 4/0 ») se dit souvent une phrase avant ou après le passage que
    le fait cite. Elle doit avoir été prononcée — jamais déduite."""
    valeurs_dites = {f.value for f in evidence if isinstance(f.value, str)}
    texte = _normaliser(" ".join(s.text for s in segments))
    mots = set(texte.split())
    absents: list[str] = []
    for slot, value in procedure.structured_data.items():
        if not isinstance(value, str) or value in valeurs_dites:
            continue
        if any(slot in f.concept for f in evidence) or _dit(value, texte, mots):
            continue
        absents.append(slot)
    return absents


def retirer_donnees_non_dites(
    procedures: list[Procedure], facts: list[ClinicalFact], segments: list[TranscriptSegment]
) -> tuple[list[Procedure], int]:
    """Dernier recours de l'extraction : plutôt que de perdre toute la consultation pour
    une précision d'acte non retrouvée dans les paroles, on retire **cette précision** —
    jamais on ne l'invente. L'emplacement redevient vide ; s'il est important, le compte
    rendu opératoire le signale « à compléter » au praticien."""
    by_id = {f.fact_id: f for f in facts}
    nettoyees: list[Procedure] = []
    retirees = 0
    for procedure in procedures:
        evidence = [by_id[i] for i in procedure.evidence_fact_ids if i in by_id]
        absents = set(donnees_non_dites(procedure, evidence, segments))
        if absents:
            retirees += len(absents)
            procedure = procedure.model_copy(
                update={
                    "structured_data": {
                        k: v for k, v in procedure.structured_data.items() if k not in absents
                    }
                }
            )
        nettoyees.append(procedure)
    return nettoyees, retirees


def resolve(
    facts: list[ClinicalFact],
    plan: TreatmentPlan | None,
    procedures: list[Procedure],
    segments: list[TranscriptSegment],
    from_extraction: bool = False,
) -> list[Violation]:
    """Toutes les violations ; liste vide = sortie acceptable.

    `from_extraction` : sortie d'un fournisseur (et non correction du praticien).
    """
    return (
        check_facts(facts, segments, from_extraction)
        + check_plan(plan, facts)
        + check_procedures(procedures, facts, segments)
    )


#: Ce que chaque règle reproche, en une phrase, à l'intention du modèle qui reprend sa
#: copie. Un refus réduit à son code (« PATIENT_PROMOTED_TO_CLINICIAN (f12) ») ne dit pas
#: quoi corriger : le modèle a reproposé trois fois la même faute sur une consultation de
#: trente-trois minutes, et le praticien n'a eu aucun compte rendu (BENTALEB, 09/10/2026).
EXPLICATIONS: dict[str, str] = {
    "DUPLICATE_FACT_ID": "deux faits portent le même fact_id : donne à chacun le sien.",
    "EVIDENCE_MISSING": "ce fait ne cite aucun passage : tout fait doit renvoyer aux paroles "
    "qui le justifient (evidence_segment_ids), ou disparaître.",
    "EVIDENCE_UNKNOWN": "ce fait cite un segment_id qui n'existe pas dans la consultation : "
    "recopie exactement les identifiants fournis.",
    "EVIDENCE_IS_AUDIO_GAP": "ce fait ne s'appuie que sur un passage où le son manquait : "
    "rien n'y a été entendu, le fait ne peut pas en sortir.",
    "EXTRACTION_SELF_VALIDATED": "manually_validated doit rester faux : seul le praticien "
    "valide un fait, jamais l'extraction.",
    "PERFORMED_IN_FUTURE": "un acte annoncé pour plus tard ne peut pas être « performed » : "
    "mets temporality à « future » avec un statut de projet, ou le statut à « performed » "
    "seulement si l'acte a été fait pendant la séance.",
    "PATIENT_PROMOTED_TO_CLINICIAN": "ce fait est attribué à la parole du patient "
    "(speaker_role « patient ») alors que son statut ou sa catégorie supposent un constat "
    "ou un diagnostic du praticien. Soit le passage cité est en réalité la parole du "
    "praticien — cite-le et mets speaker_role en conséquence —, soit le fait doit redevenir "
    "ce qu'il est : un propos du patient (clinical_status « patient_reported »).",
    "UNCERTAINTY_LOST": "un fait « uncertain » ne peut pas être « certain » : garde "
    "l'incertitude telle qu'elle a été dite.",
    "PLAN_EVIDENCE_UNKNOWN": "cet élément de plan cite un fact_id inconnu : ne cite que des "
    "faits de ta propre sortie.",
    "PLAN_ITEM_WITHOUT_EVIDENCE": "cet élément de plan ne s'appuie sur aucun fait : rattache-le "
    "aux faits qui le justifient, ou retire-le.",
    "PLAN_STATUS_UNSUPPORTED": "le statut de cet élément de plan n'est porté par aucun des "
    "faits cités : un traitement ne devient « accepté » que si un fait dit qu'il a été "
    "accepté, « proposé » que si un fait dit qu'il a été proposé, et ainsi de suite.",
    "PLAN_TEETH_UNSUPPORTED": "cet élément de plan porte une dent qu'aucun fait cité ne "
    "mentionne : n'ajoute aucune dent qui ne vienne des faits.",
    "PROCEDURE_EVIDENCE_UNKNOWN": "cet acte ne cite aucun fait, ou un fact_id inconnu : "
    "rattache-le aux faits de ta sortie.",
    "PROCEDURE_STATUS_UNSUPPORTED": "le statut de cet acte n'est porté par aucun des faits "
    "cités : un acte n'est « réalisé » que si un fait dit qu'il l'a été.",
    "PROCEDURE_DATA_UNSUPPORTED": "une donnée de cet acte (structured_data) n'a été ni "
    "prononcée dans les passages cités, ni nommée par un fait : ne remplis que ce qui a été "
    "dit, laisse le reste vide.",
}


def explication(violations: list[Violation]) -> str:
    """Les reproches d'une sortie refusée, dits en français, sans doublon."""
    vues: list[str] = []
    for violation in violations:
        phrase = EXPLICATIONS.get(violation.rule)
        if phrase and phrase not in vues:
            vues.append(phrase)
    return " ".join(vues)
