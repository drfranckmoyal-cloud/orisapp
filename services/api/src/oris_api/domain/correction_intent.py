"""Interprétation d'une correction dictée ou écrite (spec §46–47).

Une phrase du praticien devient un **patch structuré** sur l'objet clinique, jamais une
retouche du texte. Le principe est le même que pour l'extraction : ce qui n'est pas
clair n'est pas deviné. Une commande ambiguë est rendue au praticien, avec la raison et
les cibles possibles ; une commande de style ne touche pas au dossier clinique.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Literal

from oris_api.contracts import ClinicalEncounter
from oris_api.contracts.generated import TreatmentPlanItemStatus
from oris_api.domain.corrections import (
    CorrectionOperation,
    FactChanges,
    RemoveFact,
    ReplaceTooth,
    SetPlanItemStatus,
    UpdateFact,
)
from oris_api.ontology.labels import CONCEPTS

Kind = Literal["clinical", "editorial", "unclear"]
Impact = Literal["normal", "high"]

TOOTH = r"(1[1-8]|2[1-8]|3[1-8]|4[1-8]|5[1-5]|6[1-5]|7[1-5]|8[1-5])"

# « Remplace 26 par 27 », « la 26 c'est la 27 », « pas la 26, la 27 ».
REPLACE_PATTERNS = (
    re.compile(rf"\bremplace[rz]?\s+(?:la\s+)?{TOOTH}\s+par\s+(?:la\s+)?{TOOTH}\b"),
    re.compile(rf"\bpas\s+(?:la\s+)?{TOOTH}[,\s]+(?:mais\s+)?(?:la\s+)?{TOOTH}\b"),
    re.compile(rf"\b(?:la\s+)?{TOOTH}\s+c'est\s+(?:la\s+)?{TOOTH}\b"),
    re.compile(rf"\bcorrige[rz]?\s+(?:la\s+)?{TOOTH}\s+en\s+(?:la\s+)?{TOOTH}\b"),
)

# « ça concerne aussi la 12 », « la facette concerne aussi la 12 ».
ALSO_TOOTH = re.compile(rf"\b(?:concerne|porte\s+sur|touche)\s+aussi\s+(?:la\s+|les\s+)?{TOOTH}\b")

# Décisions du patient et du praticien.
STATUS_PATTERNS: tuple[tuple[re.Pattern[str], TreatmentPlanItemStatus], ...] = (
    (
        re.compile(r"\ba\s+(?:finalement\s+)?accept|\baccepte\b|\bvalide\b|\bd'accord pour\b"),
        "accepted",
    ),
    (re.compile(r"\brefus"), "refused"),
    (re.compile(r"\brepous|\breport|\bplus tard\b|\bdiffèr|\bdiffer"), "deferred"),
    (re.compile(r"\bprogramm|\bprévu\b|\bprevu\b|\bon planifie\b"), "planned"),
    (re.compile(r"\bréalisé\b|\brealise\b|\bfait aujourd'hui\b|\bterminé\b"), "completed"),
    (re.compile(r"\bproposé\b|\bpropose\b"), "proposed"),
)

# « Retire la phrase sur la sensibilité », « supprime le fait sur la douleur ».
REMOVE = re.compile(r"\b(?:retire[rz]?|supprime[rz]?|enlève[rz]?|efface[rz]?)\b")

# Préférences de rédaction : elles ne touchent jamais l'objet clinique (§46 B).
EDITORIAL = (
    (re.compile(r"\bplus court|\braccourci|\bcondense|\brésume\b"), "compte rendu plus court"),
    (re.compile(r"\bplus (?:long|détaillé|detaille)|\bdéveloppe\b"), "compte rendu plus détaillé"),
    (re.compile(r"\breformule|\bréécri|\breecri|\bstyle\b|\bton\b"), "autre formulation"),
)

STATUS_LABELS: dict[str, str] = {
    "discussed": "discuté",
    "proposed": "proposé",
    "accepted": "accepté",
    "refused": "refusé",
    "deferred": "reporté",
    "planned": "prévu",
    "completed": "réalisé",
}


@dataclass(frozen=True)
class Interpretation:
    """Ce qu'Oris a compris — et ce qu'il refuse de deviner."""

    kind: Kind
    summary: str
    operations: list[CorrectionOperation] = field(default_factory=list)
    impact: Impact = "normal"
    reason: str = ""
    candidates: list[str] = field(default_factory=list)
    preference: str = ""


def normalize(command: str) -> str:
    """Minuscules, apostrophes droites, accents conservés (ils portent du sens)."""
    text = unicodedata.normalize("NFC", command).strip().lower()
    return text.replace("’", "'").replace(" ", " ")


def words(text: str) -> set[str]:
    return {w for w in re.split(r"[^a-zà-ÿ0-9]+", text) if len(w) > 3}


def fact_haystack(encounter: ClinicalEncounter, fact_id: str) -> str:
    fact = next((f for f in encounter.facts if f.fact_id == fact_id), None)
    if fact is None:
        return ""
    label = CONCEPTS.get(fact.concept)
    parts = [fact.concept, label.label if label else "", str(fact.value or "")]
    return normalize(" ".join(parts))


def describe_fact(encounter: ClinicalEncounter, fact_id: str) -> str:
    """Comment nommer un élément au praticien : en français, avec ses dents."""
    fact = next((f for f in encounter.facts if f.fact_id == fact_id), None)
    if fact is None:
        return fact_id
    label = CONCEPTS.get(fact.concept)
    name = str(fact.value).strip() if isinstance(fact.value, str) and fact.value.strip() else ""
    written = name or (label.label if label else fact.concept)
    teeth = f" ({', '.join(fact.teeth)})" if fact.teeth else ""
    return f"{written}{teeth}"


def matching_facts(encounter: ClinicalEncounter, command: str) -> list[str]:
    """Faits dont le sujet apparaît dans la commande."""
    asked = words(command)
    found = []
    for fact in encounter.facts:
        subject = words(fact_haystack(encounter, fact.fact_id))
        if subject & asked:
            found.append(fact.fact_id)
    return found


def matching_plan_items(encounter: ClinicalEncounter, command: str) -> list[str]:
    plan = encounter.treatment_plan
    if plan is None:
        return []
    asked = words(command)
    return [item.item_id for item in plan.items if words(normalize(item.action)) & asked]


def only_plan_item(encounter: ClinicalEncounter) -> str | None:
    plan = encounter.treatment_plan
    if plan is not None and len(plan.items) == 1:
        return plan.items[0].item_id
    return None


def teeth_in(encounter: ClinicalEncounter, tooth: str) -> list[str]:
    return [fact.fact_id for fact in encounter.facts if tooth in fact.teeth]


def unclear(reason: str, candidates: list[str] | None = None) -> Interpretation:
    return Interpretation(
        kind="unclear",
        summary="Commande non comprise",
        reason=reason,
        candidates=candidates or [],
    )


def interpret(command: str, encounter: ClinicalEncounter) -> Interpretation:
    """Phrase du praticien → patch structuré, ou refus explicite."""
    text = normalize(command)
    if not text:
        return unclear("Rien n'a été dit.")

    for pattern, preference in EDITORIAL:
        if pattern.search(text):
            return Interpretation(
                kind="editorial",
                summary=f"Préférence de rédaction : {preference}",
                preference=preference,
                reason="Le dossier clinique n'est pas modifié : c'est une question de forme.",
            )

    for pattern in REPLACE_PATTERNS:
        found = pattern.search(text)
        if found:
            old, new = found.group(1), found.group(2)
            concerned = teeth_in(encounter, old)
            if not concerned:
                return unclear(f"Aucun élément ne porte la dent {old}.")
            return Interpretation(
                kind="clinical",
                summary=f"Remplacer la dent {old} par {new} ({len(concerned)} élément(s))",
                operations=[ReplaceTooth(operation="replace_tooth", from_tooth=old, to_tooth=new)],
                impact="high",
            )

    also = ALSO_TOOTH.search(text)
    if also:
        tooth = also.group(1)
        facts = matching_facts(encounter, text)
        if len(facts) != 1:
            return unclear(
                "Précisez de quel élément il s'agit.",
                candidates=[describe_fact(encounter, fid) for fid in facts],
            )
        fact = next(f for f in encounter.facts if f.fact_id == facts[0])
        if tooth in fact.teeth:
            return unclear(f"Cet élément porte déjà la dent {tooth}.")
        return Interpretation(
            kind="clinical",
            summary=f"Ajouter la dent {tooth} à « {fact.value or fact.concept} »",
            operations=[
                UpdateFact(
                    operation="update_fact",
                    fact_id=fact.fact_id,
                    changes=FactChanges(teeth=[*fact.teeth, tooth]),
                )
            ],
        )

    if REMOVE.search(text):
        facts = matching_facts(encounter, text)
        if len(facts) != 1:
            return unclear(
                "Précisez ce qu'il faut retirer.",
                candidates=[describe_fact(encounter, fid) for fid in facts],
            )
        fact = next(f for f in encounter.facts if f.fact_id == facts[0])
        return Interpretation(
            kind="clinical",
            summary=f"Retirer « {fact.value or fact.concept} » du dossier",
            operations=[RemoveFact(operation="remove_fact", fact_id=fact.fact_id)],
            impact="high",
        )

    for pattern, status in STATUS_PATTERNS:
        if not pattern.search(text):
            continue
        single = only_plan_item(encounter)
        items = matching_plan_items(encounter, text) or ([single] if single else [])
        if len(items) != 1:
            plan = encounter.treatment_plan
            return unclear(
                "Précisez quel traitement change de statut.",
                candidates=[item.action for item in plan.items] if plan else [],
            )
        return Interpretation(
            kind="clinical",
            summary=f"Statut du traitement → {STATUS_LABELS[status]}",
            operations=[
                SetPlanItemStatus(operation="set_plan_item_status", item_id=items[0], status=status)
            ],
            impact="high" if status in {"accepted", "refused", "completed"} else "normal",
        )

    return unclear(
        "Oris n'a pas reconnu de correction. Reformulez, par exemple : "
        "« remplace 26 par 27 », « le patient a accepté les composites », "
        "« retire la phrase sur la sensibilité »."
    )
