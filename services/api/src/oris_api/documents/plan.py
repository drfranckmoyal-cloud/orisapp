"""Le plan de traitement, mis en forme pour être lu d'un coup d'œil.

Une étape par élément du plan, avec un titre court, ses dents, ses précisions et le
délai qu'elle annonce ; une chronologie ; ce qui a été écarté ; les dents absentes pour
le schéma. Rien n'est ajouté au plan : les titres et les délais sont **pris dans ce qui
a été dit**, jamais calculés.

Ordre : si chaque étape a un rang dit (« en premier lieu », « ensuite »), elles sont
numérotées dans cet ordre. Sinon elles gardent l'ordre de la dictée, sans numéro — un
numéro inventé serait une chronologie inventée (décision du 21/09/2026).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from oris_api.contracts import ClinicalEncounter, TreatmentPlanItem
from oris_api.ontology.labels import CONCEPTS, translate_value

STATUT: dict[str, str] = {
    "discussed": "discuté",
    "proposed": "proposé",
    "accepted": "accepté",
    "refused": "refusé",
    "deferred": "reporté",
    "planned": "prévu",
    "completed": "réalisé",
}
ECARTES = frozenset({"refused"})
#: « 8 semaines », « 2 h », « 3 mois » : un délai tel qu'il a été dit.
DELAI = re.compile(
    r"\b(\d+(?:[.,]\d+)?\s*(?:semaines?|jours?|mois|ans?|heures?|h|minutes?|min))\b",
    re.IGNORECASE,
)
TITRE_MAX = 58
ABSENCES = frozenset({"missing_tooth", "agenesis", "tooth_agenesis", "edentulous_space"})


@dataclass(frozen=True)
class Etape:
    titre: str
    rang: int | None
    dents: tuple[str, ...]
    details: tuple[str, ...]
    statut: str
    delai: str | None
    fact_ids: tuple[str, ...]
    couleur: int = 0


@dataclass(frozen=True)
class PlanVue:
    numerote: bool
    etapes: tuple[Etape, ...]
    ecartes: tuple[Etape, ...]
    dents_absentes: tuple[str, ...]
    chronologie: tuple[tuple[str, str | None], ...] = field(default_factory=tuple)

    @property
    def vide(self) -> bool:
        return not self.etapes and not self.ecartes


def _titre_et_reste(action: str) -> tuple[str, str | None]:
    """Un titre court tiré de l'action ; le reste devient une précision."""
    texte = action.strip().rstrip(".")
    texte = texte[:1].upper() + texte[1:]
    if len(texte) <= TITRE_MAX:
        return texte, None
    for coupe in (" (", " — ", " : ", ", "):
        position = texte.find(coupe)
        if 12 <= position <= TITRE_MAX:
            reste = texte[position + len(coupe) :].rstrip(")").strip()
            return texte[:position], (reste[:1].upper() + reste[1:]) if reste else None
    return texte, None


def _mot(valeur: str) -> str:
    """Un code du vocabulaire d'Oris (« implant_option ») dit en français."""
    if valeur in CONCEPTS:
        return CONCEPTS[valeur].label
    return translate_value(valeur) or valeur


def _liste(valeurs: list[str]) -> str:
    return ", ".join(_mot(v) for v in valeurs)


def _etape(item: TreatmentPlanItem, rang: int | None, couleur: int) -> Etape:
    titre, reste = _titre_et_reste(item.action)
    details: list[str] = []
    if reste:
        details.append(f"{reste}.")
    if item.problem:
        details.append(f"Motif : {item.problem.rstrip('.')}.")
    if item.prerequisites:
        details.append(f"Préalables : {_liste(item.prerequisites)}.")
    if item.alternatives:
        details.append(f"Alternatives évoquées : {_liste(item.alternatives)}.")
    if item.uncertainties:
        details.append(f"Incertitudes : {_liste(item.uncertainties)}.")
    delai = DELAI.search(item.action)
    return Etape(
        titre=titre,
        rang=rang,
        dents=tuple(item.teeth),
        details=tuple(details),
        statut=STATUT[item.status],
        delai=delai.group(1) if delai else None,
        fact_ids=tuple(item.evidence_fact_ids),
        couleur=couleur,
    )


def plan_vue(encounter: ClinicalEncounter) -> PlanVue:
    plan = encounter.treatment_plan
    items = list(plan.items) if plan else []
    retenus = [i for i in items if i.status not in ECARTES]
    ecartes = [i for i in items if i.status in ECARTES]

    numerote = bool(retenus) and all(i.sequence is not None for i in retenus)
    if numerote:
        retenus.sort(key=lambda i: i.sequence or 0)
    etapes = tuple(
        _etape(item, index + 1 if numerote else None, index) for index, item in enumerate(retenus)
    )
    absentes = sorted(
        {
            tooth
            for fact in encounter.facts
            if fact.concept in ABSENCES and fact.assertion == "present"
            for tooth in fact.teeth
        }
    )
    return PlanVue(
        numerote=numerote,
        etapes=etapes,
        ecartes=tuple(_etape(item, None, -1) for item in ecartes),
        dents_absentes=tuple(absentes),
        chronologie=tuple((etape.titre, etape.delai) for etape in etapes),
    )


def entete(etape: Etape) -> str:
    return f"Étape {etape.rang} — {etape.titre}" if etape.rang else etape.titre
