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
    item_id: str
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


#: Tournures d'introduction qui n'apportent rien à un titre (« Réalisation de 2 bridges »).
ENTREES = re.compile(
    r"^(réalisation|mise en place|pose|port|séance|réalisation d'une|prise en charge)"
    r"\s+(de la|de l'|des|du|de|d'une|d'un|d')\s*",
    re.IGNORECASE,
)
#: Où couper : au-delà, ce sont des précisions (matériau, durée, moyen, suite).
COUPES = (" avec ", " pendant ", " en ", " puis ", " après ", " (", ", ", " pour ", " sur ", " — ")
MOTS_OUTILS = frozenset(
    {
        "de",
        "des",
        "du",
        "d'",
        "la",
        "le",
        "les",
        "l'",
        "en",
        "avec",
        "pour",
        "puis",
        "et",
        "à",
        "au",
        "aux",
        "une",
        "un",
        "sur",
        "par",
    }
)
MOTS_TITRE = 4


def titre_court(action: str) -> str:
    """Trois ou quatre mots tirés de l'action, sans en inventer aucun."""
    texte = action.strip().rstrip(".")
    sans_entree = ENTREES.sub("", texte)
    if len(sans_entree.split()) >= 1:
        texte = sans_entree
    coupe = min((texte.find(c) for c in COUPES if texte.find(c) > 0), default=len(texte))
    mots = texte[:coupe].split()[:MOTS_TITRE]
    while mots and mots[-1].lower() in MOTS_OUTILS:
        mots.pop()
    titre = " ".join(mots) or action.strip()
    return titre[:1].upper() + titre[1:]


def _action_complete(action: str) -> str:
    texte = action.strip().rstrip(".")
    return f"{texte[:1].upper()}{texte[1:]}."


def _mot(valeur: str) -> str:
    """Un code du vocabulaire d'Oris (« implant_option ») dit en français."""
    if valeur in CONCEPTS:
        return CONCEPTS[valeur].label
    return translate_value(valeur) or valeur


def _liste(valeurs: list[str]) -> str:
    return ", ".join(_mot(v) for v in valeurs)


def _etape(
    item: TreatmentPlanItem, rang: int | None, couleur: int, titre: str | None = None
) -> Etape:
    titre = titre or titre_court(item.action)
    details: list[str] = []
    # L'action telle qu'elle a été dite vient en tête des précisions, sauf si le titre
    # la dit déjà toute entière.
    if titre.rstrip(".").lower() != item.action.strip().rstrip(".").lower():
        details.append(_action_complete(item.action))
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
        item_id=item.item_id,
        titre=titre,
        rang=rang,
        dents=tuple(item.teeth),
        details=tuple(details),
        statut=STATUT[item.status],
        delai=delai.group(1) if delai else None,
        fact_ids=tuple(item.evidence_fact_ids),
        couleur=couleur,
    )


def plan_vue(encounter: ClinicalEncounter, titres: dict[str, str] | None = None) -> PlanVue:
    """`titres` : titres courts rédigés et contrôlés (llm/redaction.py) ; à défaut, les
    règles de `titre_court`."""
    titres = titres or {}
    plan = encounter.treatment_plan
    items = list(plan.items) if plan else []
    retenus = [i for i in items if i.status not in ECARTES]
    ecartes = [i for i in items if i.status in ECARTES]

    numerote = bool(retenus) and all(i.sequence is not None for i in retenus)
    if numerote:
        retenus.sort(key=lambda i: i.sequence or 0)
    etapes = tuple(
        _etape(item, index + 1 if numerote else None, index, titres.get(item.item_id))
        for index, item in enumerate(retenus)
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
        ecartes=tuple(_etape(item, None, -1, titres.get(item.item_id)) for item in ecartes),
        dents_absentes=tuple(absentes),
        chronologie=tuple((etape.titre, etape.delai) for etape in etapes),
    )


def entete(etape: Etape) -> str:
    return f"Étape {etape.rang} — {etape.titre}" if etape.rang else etape.titre


def titres_depuis(claims: list[dict[str, object]]) -> dict[str, str]:
    """Les titres courts d'une version enregistrée du plan, élément par élément."""
    titres: dict[str, str] = {}
    for claim in claims:
        item_id = str(claim.get("item_id") or "")
        section = str(claim.get("section") or "")
        if not item_id or item_id in titres or section == "Chronologie":
            continue
        if section == "Écarté":
            # « Pose d'implants (12, 22) — refusé. » : le titre est avant les dents.
            titre = str(claim.get("text") or "").split(" — ", 1)[0].split(" (", 1)[0]
            titres[item_id] = titre
            continue
        titres[item_id] = section.split(" — ", 1)[1] if section.startswith("Étape ") else section
    return titres
