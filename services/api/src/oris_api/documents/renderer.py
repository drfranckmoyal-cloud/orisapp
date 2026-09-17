"""Rédaction déterministe des documents depuis l'objet clinique (spec §32–34).

Entrée : l'objet clinique uniquement, jamais le transcript (D008).
Chaque phrase est un `Claim` qui porte les faits qui l'appuient.

La formulation dépend des axes du fait, jamais d'une supposition :
- négation → « absence de », « non constaté », « non retenu » ;
- incertitude → « suspicion de …, non confirmée », « impression du patient » ;
- statut → « option discutée », « proposé », « accepté », « prévu », « réalisé » ;
- temporalité → « évoqué antérieurement », « antécédent ».
Les sections vides ne sont pas affichées (§32.1).
"""

from __future__ import annotations

from collections.abc import Iterable

from oris_api.contracts import ClinicalEncounter, ClinicalFact, TreatmentPlanItem
from oris_api.domain.types import Claim, GeneratedDocument
from oris_api.ontology.labels import label_for, translate_value

LIMITS_SECTION = "Limites du compte rendu"
NON_EXHAUSTIVE = "Le compte rendu ne peut pas être considéré comme exhaustif."
UNRENDERED_PREFIX = "À rédiger"

SECTION_ORDER = (
    ("Motif de consultation", {"chief_complaint"}),
    ("Éléments anamnestiques", {"history", "medication"}),
    ("Symptômes rapportés", {"symptom"}),
    ("Examen clinique", {"clinical_finding"}),
    ("Examens complémentaires", {"radiographic_finding"}),
    ("Analyse / diagnostic / hypothèses", {"assessment", "diagnosis"}),
    ("Options thérapeutiques discutées", {"treatment_option"}),
    ("Décision / plan retenu", {"treatment_decision"}),
    ("Actes réalisés", {"procedure", "material"}),
    ("Informations données au patient", {"patient_information"}),
    ("Suite / contrôle", {"follow_up"}),
    ("Autres éléments", {"other"}),
)

PLAN_STATUS_LABELS = {
    "discussed": "discuté",
    "proposed": "proposé",
    "accepted": "accepté",
    "refused": "refusé",
    "deferred": "reporté",
    "planned": "prévu",
    "completed": "réalisé",
}


def teeth_suffix(teeth: Iterable[str]) -> str:
    teeth = list(teeth)
    return f" ({', '.join(teeth)})" if teeth else ""


def capitalize(text: str) -> str:
    return text[:1].upper() + text[1:]


def de(noun: str) -> str:
    """« de fissure », « d’hypersensibilité »."""
    return f"d’{noun}" if noun[:1].lower() in "aeéèêiïoôuh" else f"de {noun}"


def fact_phrase(fact: ClinicalFact) -> str | None:
    """Groupe nominal du fait (libellé, valeur dite, dents), ou None si concept inconnu."""
    known = label_for(fact.concept, fact.category)
    if known is None:
        return None
    value = translate_value(fact.value)
    teeth = teeth_suffix(fact.teeth)
    match known.value_mode:
        case "value_only":
            return f"{value or known.label}{teeth}"
        case "show" if value and value != known.label:
            return f"{known.label} : {value}{teeth}"
        case _:
            return f"{known.label}{teeth}"


def fact_sentence(fact: ClinicalFact) -> str:
    known = label_for(fact.concept, fact.category)
    phrase = fact_phrase(fact)
    if known is None or phrase is None:
        return f"{UNRENDERED_PREFIX} : élément « {fact.concept} » non reconnu par Oris."
    absent = fact.assertion == "absent"
    unsure = fact.assertion == "uncertain" or fact.certainty in {"possible", "probable"}
    status = fact.clinical_status

    if known.value_mode == "statement":
        value = translate_value(fact.value) or ("non" if absent else "oui")
        return f"{capitalize(known.label)}{teeth_suffix(fact.teeth)} : {value}."

    if fact.category == "medication":
        if absent:
            detail = translate_value(fact.value)
            suffix = f" ({detail})" if detail and detail != known.label else ""
            return f"{capitalize(known.label)} : n’est plus pris actuellement{suffix}."
        return f"Traitement en cours rapporté par le patient : {phrase}."

    if fact.category == "material":
        return f"Matériau utilisé — {phrase}."

    match status:
        case "patient_reported":
            if absent:
                return f"Rapporté par le patient : absence {de(phrase)}."
            if fact.temporality == "past":
                return f"Antécédent rapporté par le patient : {phrase}."
            if unsure:
                return f"Impression du patient, non confirmée : {phrase}."
            return f"Rapporté par le patient : {phrase}."
        case "observed":
            if absent:
                return f"Non constaté : {phrase}."
            if unsure:
                return f"Constat incertain : {phrase}."
            return f"Constaté : {phrase}."
        case "clinician_assessment":
            if absent:
                return f"Non retenu à ce stade : {phrase}."
            if fact.assertion == "uncertain" or fact.certainty == "unknown":
                return f"Évaluation non conclue : {phrase}."
            if unsure:
                return f"Hypothèse ({fact.certainty}) : {phrase}."
            return f"Évaluation : {phrase}."
        case "differential":
            if absent:
                return f"Hypothèse écartée : {phrase}."
            return f"Suspicion {de(phrase)}, non confirmée."
        case "discussed":
            if absent:
                return f"Option écartée : {phrase}."
            if fact.temporality == "past":
                return f"Option évoquée antérieurement : {phrase}."
            return f"Option discutée : {phrase}."
        case "proposed":
            prefix = "Proposé antérieurement" if fact.temporality == "past" else "Proposé"
            return f"{prefix} : {phrase}."
        case "accepted":
            return f"Accepté : {phrase}."
        case "refused":
            return f"Refusé : {phrase}."
        case "deferred":
            return f"Reporté : {phrase}."
        case "planned":
            return f"Prévu : {phrase}."
        case "performed":
            return f"Non réalisé : {phrase}." if absent else f"Réalisé : {phrase}."
    return f"{UNRENDERED_PREFIX} : statut « {status} » non pris en charge."


def render_content(claims: Iterable[Claim]) -> str:
    blocks: list[str] = []
    current: str | None = None
    for claim in claims:
        if claim.section != current:
            if blocks:
                blocks.append("")
            blocks.append(claim.section)
            current = claim.section
        blocks.append(claim.text)
    return "\n".join(blocks)


def limits_claims(encounter: ClinicalEncounter) -> list[Claim]:
    return [
        Claim(
            section=LIMITS_SECTION,
            text=f"{warning.message} {NON_EXHAUSTIVE}",
            warning_codes=(warning.code,),
        )
        for warning in encounter.warnings
        if warning.severity == "critical"
    ]


def render_consultation_note(encounter: ClinicalEncounter) -> GeneratedDocument:
    claims = limits_claims(encounter)
    for section, categories in SECTION_ORDER:
        for fact in encounter.facts:
            if fact.category in categories:
                claims.append(Claim(section, fact_sentence(fact), fact_ids=(fact.fact_id,)))
    return GeneratedDocument("consultation_note", render_content(claims), tuple(claims))


def plan_item_sentence(item: TreatmentPlanItem) -> str:
    teeth = f"{', '.join(item.teeth)} — " if item.teeth else ""
    number = f"{item.sequence}. " if item.sequence is not None else ""
    parts = [f"{number}{teeth}{item.action} — statut : {PLAN_STATUS_LABELS[item.status]}"]
    if item.problem:
        parts.append(f"motif : {item.problem}")
    if item.alternatives:
        parts.append(f"alternatives : {', '.join(item.alternatives)}")
    if item.prerequisites:
        parts.append(f"préalables : {', '.join(item.prerequisites)}")
    if item.uncertainties:
        parts.append(f"incertitudes : {', '.join(item.uncertainties)}")
    return " ; ".join(parts) + "."


def render_treatment_plan(encounter: ClinicalEncounter) -> GeneratedDocument:
    claims = limits_claims(encounter)
    plan = encounter.treatment_plan
    if plan is not None:
        # Numérotation uniquement si la séquence a été énoncée (§33.3).
        items = sorted(plan.items, key=lambda i: (i.sequence is None, i.sequence or 0))
        for item in items:
            claims.append(
                Claim(
                    "Plan de traitement",
                    plan_item_sentence(item),
                    fact_ids=tuple(item.evidence_fact_ids),
                )
            )
        # Les objectifs (`goals`) ne portent pas de faits d'appui dans le schéma :
        # ils ne sont pas rédigés tant qu'ils ne peuvent pas être justifiés.
    return GeneratedDocument("treatment_plan_text", render_content(claims), tuple(claims))
