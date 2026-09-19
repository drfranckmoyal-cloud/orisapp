"""Modèles de comptes rendus opératoires (spec §37–45).

Un modèle n'est **pas** un paragraphe prérempli où l'IA comblerait les trous (§77) :
c'est une liste ordonnée d'emplacements. Un emplacement non renseigné n'apparaît pas,
et rien n'est jamais rempli à la place du praticien — ni son adhésif habituel, ni une
étape « normalement » réalisée (§37).

Un emplacement marqué important qui reste vide **alerte**, il ne se remplit pas (§45).
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal

from oris_api.contracts.generated import ProcedureProcedureType

SlotKind = Literal["text", "flag"]

# Ordre de présentation du document (§37).
SECTIONS = (
    "Indication",
    "Site opératoire",
    "Anesthésie",
    "Isolation",
    "Préparation",
    "Étapes réalisées",
    "Matériaux utilisés",
    "Contrôle et finition",
    "Complications",
    "Consignes et suite",
)


@dataclass(frozen=True)
class Slot:
    """Un emplacement de preuve : renseigné, il s'écrit ; vide, il n'existe pas.

    `concepts` : les faits qui peuvent le renseigner. Un emplacement n'est jamais rempli
    par habitude — mais une information **dite pendant l'intervention** et déjà retenue
    comme fait appartient à l'acte : le document la place au bon endroit, en citant le
    fait qui la porte.
    """

    key: str
    label: str
    section: str
    kind: SlotKind = "text"
    important: bool = False
    concepts: tuple[str, ...] = ()


def text(
    key: str, label: str, section: str, important: bool = False, concepts: tuple[str, ...] = ()
) -> Slot:
    return Slot(key, label, section, "text", important, concepts)


def flag(
    key: str, label: str, section: str, important: bool = False, concepts: tuple[str, ...] = ()
) -> Slot:
    return Slot(key, label, section, "flag", important, concepts)


COMPOSITE = (
    text("indication", "indication", "Indication"),
    text("surface", "face", "Site opératoire"),
    text("anesthesia", "anesthésie", "Anesthésie"),
    flag("isolation", "isolation du champ opératoire", "Isolation"),
    flag("old_restoration_removed", "dépose de l'ancienne restauration", "Préparation"),
    text("preparation", "préparation", "Préparation"),
    text("pulp_protection", "protection pulpaire", "Préparation"),
    text("adhesive_protocol", "protocole adhésif", "Étapes réalisées"),
    text("matrix", "matrice", "Étapes réalisées"),
    text("layering", "stratification", "Étapes réalisées"),
    text("contact_point", "point de contact", "Étapes réalisées"),
    text("adhesive", "adhésif", "Matériaux utilisés", important=True),
    text("composite", "composite", "Matériaux utilisés", important=True),
    text("shade", "teinte", "Matériaux utilisés"),
    flag("finishing", "finition", "Contrôle et finition"),
    flag("polishing", "polissage", "Contrôle et finition"),
    flag("occlusal_check", "contrôle de l'occlusion", "Contrôle et finition"),
    text("complication", "complication", "Complications"),
    text("instructions", "consignes", "Consignes et suite"),
    text("next", "suite", "Consignes et suite"),
)

DIRECT_AESTHETIC = (
    text("indication", "demande et indication", "Indication"),
    text("aesthetic_plan", "plan esthétique validé", "Indication"),
    text("mockup", "mock-up ou guide", "Préparation"),
    text("anesthesia", "anesthésie", "Anesthésie"),
    flag("isolation", "isolation du champ opératoire", "Isolation"),
    text("preparation", "préparation", "Préparation"),
    text("adhesive", "adhésif", "Matériaux utilisés", important=True),
    text("composite", "composite", "Matériaux utilisés", important=True),
    text("shade", "teintes", "Matériaux utilisés"),
    text("layering", "stratification", "Étapes réalisées"),
    text("morphology", "morphologie", "Étapes réalisées"),
    text("embrasures", "embrasures et points de contact", "Étapes réalisées"),
    flag("finishing", "finition", "Contrôle et finition"),
    flag("polishing", "polissage", "Contrôle et finition"),
    flag("occlusal_check", "contrôle de l'occlusion", "Contrôle et finition"),
    flag("photographs", "photographies", "Contrôle et finition"),
    text("complication", "complication", "Complications"),
    text("next", "contrôle prévu", "Consignes et suite"),
)

VENEER_PREPARATION = (
    text("indication", "indication", "Indication"),
    text("aesthetic_validation", "validation esthétique préalable", "Indication"),
    flag("mockup_guided", "réduction guidée par mock-up", "Préparation"),
    text("anesthesia", "anesthésie", "Anesthésie"),
    text("preparation_design", "design de préparation", "Préparation"),
    text("margins", "limites", "Préparation"),
    text("enamel_preservation", "conservation d'émail", "Préparation"),
    flag("scan", "empreinte optique", "Étapes réalisées"),
    flag("shade_communicated", "communication de la teinte", "Étapes réalisées"),
    text("shade", "teinte", "Matériaux utilisés"),
    flag("provisionals", "provisoires", "Étapes réalisées"),
    text("provisional_technique", "technique des provisoires", "Étapes réalisées"),
    text("complication", "complication", "Complications"),
    text("instructions", "recommandations", "Consignes et suite"),
    text("next", "prochain rendez-vous", "Consignes et suite"),
)

VENEER_BONDING = (
    text("indication", "indication", "Indication"),
    text("restoration_type", "type de restauration", "Site opératoire"),
    flag("try_in", "essayage", "Étapes réalisées"),
    flag("patient_aesthetic_approval", "validation esthétique par le patient", "Étapes réalisées"),
    text("cement_shade", "teinte du ciment", "Matériaux utilisés"),
    flag("isolation", "isolation du champ opératoire", "Isolation"),
    text("ceramic_surface_treatment", "traitement de surface de la céramique", "Préparation"),
    text("tooth_surface_treatment", "traitement de surface dentaire", "Préparation"),
    text("adhesive", "adhésif", "Matériaux utilisés"),
    text("bonding_material", "matériau de collage", "Matériaux utilisés", important=True),
    text("light_curing", "photopolymérisation", "Étapes réalisées"),
    flag("excess_removal", "élimination des excès", "Étapes réalisées"),
    flag(
        "finish_contacts_occlusion",
        "finitions, contacts et contrôle occlusal",
        "Contrôle et finition",
    ),
    flag("photographs", "photographies", "Contrôle et finition"),
    text("complication", "complication", "Complications"),
    text("instructions", "consignes", "Consignes et suite"),
    text("next", "contrôle", "Consignes et suite"),
)

WEAR_ADDITIVE = (
    text("wear_context", "contexte d'usure", "Indication"),
    text("objective", "objectif", "Indication"),
    text("preoperative_protocol", "protocole préopératoire", "Préparation"),
    text("wax_up", "wax-up, mock-up ou clé", "Préparation"),
    text("anesthesia", "anesthésie", "Anesthésie"),
    flag("isolation", "isolation du champ opératoire", "Isolation"),
    text("support", "support", "Préparation"),
    text("adhesive", "adhésif", "Matériaux utilisés", important=True),
    text("composite", "composite", "Matériaux utilisés", important=True),
    text("shade", "teintes", "Matériaux utilisés"),
    text("additive_technique", "technique additive", "Étapes réalisées"),
    text("anatomy", "reconstruction anatomique", "Étapes réalisées"),
    flag("functional_check", "contrôle fonctionnel et occlusal", "Contrôle et finition"),
    flag("finishing", "finition et polissage", "Contrôle et finition"),
    text("complication", "complication", "Complications"),
    text("patient_information", "information donnée au patient", "Consignes et suite"),
    text("next", "suivi", "Consignes et suite"),
)

EXTRACTION = (
    text("indication", "indication", "Indication"),
    text("anesthesia", "anesthésie", "Anesthésie", important=True),
    text("approach", "type d'extraction et abord", "Étapes réalisées"),
    flag("flap", "lambeau", "Étapes réalisées"),
    flag("osteotomy", "ostéotomie", "Étapes réalisées"),
    flag("tooth_sectioning", "odontosection", "Étapes réalisées"),
    flag("curettage", "curetage alvéolaire", "Étapes réalisées"),
    flag("irrigation", "irrigation", "Étapes réalisées"),
    text("hemostasis", "hémostase", "Contrôle et finition", important=True),
    text("sutures", "sutures", "Contrôle et finition"),
    text("complication", "complication", "Complications"),
    text("prescription", "prescription", "Consignes et suite"),
    text("postop_instructions", "consignes postopératoires", "Consignes et suite", important=True),
    text("next", "suivi", "Consignes et suite"),
)

MINOR_SURGERY_GENERIC = (
    text("indication", "indication", "Indication"),
    text("site", "site", "Site opératoire"),
    text("anesthesia", "anesthésie", "Anesthésie", important=True),
    text("approach", "incision et abord", "Étapes réalisées"),
    text("gesture", "geste réalisé", "Étapes réalisées", important=True),
    text("material", "matériel ou biomatériau", "Matériaux utilisés"),
    text("hemostasis", "hémostase", "Contrôle et finition"),
    text("sutures", "sutures", "Contrôle et finition"),
    text("complication", "incident ou complication", "Complications"),
    text("instructions", "consignes", "Consignes et suite"),
    text("next", "contrôle", "Consignes et suite"),
)

# Quel fait peut renseigner quel emplacement. Un emplacement n'est jamais rempli par
# habitude : cette table ne fait que **placer au bon endroit** une information déjà dite
# et retenue comme fait, en citant ce fait. Ce qui n'a pas été dit reste absent.
FACT_SOURCES: dict[str, dict[str, tuple[str, ...]]] = {
    "composite": {
        "anesthesia": ("local_anesthesia",),
        "isolation": ("isolation",),
        "preparation": ("cavity_preparation",),
        "pulp_protection": ("pulp_capping",),
        "matrix": ("matrix",),
        "layering": ("layering", "layered_composite"),
        "adhesive": ("adhesive", "bonding_system"),
        "composite": ("composite",),
        "shade": ("shade", "shade_selection", "composite_shade"),
        "finishing": ("finishing_polishing", "finishing_polishing_occlusion"),
        "polishing": ("polishing",),
        "occlusal_check": ("occlusal_check", "occlusal_adjustment"),
        "complication": ("complication",),
        "next": ("next_visit", "post_treatment_check"),
    },
    "direct_aesthetic": {
        "mockup": ("mock_up", "wax_up"),
        "anesthesia": ("local_anesthesia",),
        "isolation": ("isolation",),
        "adhesive": ("adhesive", "bonding_system"),
        "composite": ("composite", "additive_composite", "injected_composite"),
        "shade": ("shade", "shade_selection"),
        "layering": ("layering", "layered_composite"),
        "finishing": ("finishing_polishing",),
        "polishing": ("polishing",),
        "occlusal_check": ("occlusal_check",),
        "photographs": ("clinical_photographs",),
        "complication": ("complication",),
        "next": ("next_visit", "post_treatment_check"),
    },
    "veneer_preparation": {
        "aesthetic_validation": ("aesthetic_approval",),
        "mockup_guided": ("mockup_guided_reduction", "mock_up"),
        "anesthesia": ("local_anesthesia",),
        "preparation_design": ("veneer_preparation",),
        "scan": ("scan", "impression"),
        "shade_communicated": ("shade_communication",),
        "shade": ("shade", "shade_selection"),
        "provisionals": ("provisionals",),
        "complication": ("complication",),
        "next": ("next_visit",),
    },
    "veneer_bonding": {
        "try_in": ("try_in",),
        "patient_aesthetic_approval": ("aesthetic_approval",),
        "isolation": ("isolation",),
        "adhesive": ("adhesive",),
        "bonding_material": ("bonding_material", "cementation"),
        "light_curing": ("light_curing",),
        "finish_contacts_occlusion": (
            "finishing_contacts_occlusion",
            "finishing_polishing_occlusion",
        ),
        "photographs": ("clinical_photographs",),
        "complication": ("complication",),
        "next": ("next_visit", "post_treatment_check"),
    },
    "wear_additive": {
        "wax_up": ("wax_up", "mock_up"),
        "anesthesia": ("local_anesthesia",),
        "isolation": ("isolation",),
        "adhesive": ("adhesive", "bonding_system"),
        "composite": ("composite", "additive_composite"),
        "shade": ("shade", "shade_selection"),
        "functional_check": ("occlusal_check",),
        "finishing": ("finishing_polishing", "polishing"),
        "complication": ("complication",),
        "next": ("next_visit", "post_treatment_check"),
    },
    "extraction": {
        "anesthesia": ("local_anesthesia",),
        "approach": ("surgical_approach",),
        "tooth_sectioning": ("root_sectioning",),
        "curettage": ("alveolar_curettage",),
        "hemostasis": ("hemostasis",),
        "sutures": ("sutures",),
        "complication": ("complication",),
        "postop_instructions": ("postoperative_instructions",),
        "next": ("next_visit", "healing_check"),
    },
    "minor_surgery_generic": {
        "anesthesia": ("local_anesthesia",),
        "approach": ("surgical_approach",),
        "hemostasis": ("hemostasis",),
        "sutures": ("sutures",),
        "complication": ("complication",),
        "instructions": ("postoperative_instructions",),
        "next": ("next_visit", "healing_check"),
    },
}


def with_sources(kind: str, slots: tuple[Slot, ...]) -> tuple[Slot, ...]:
    sources = FACT_SOURCES.get(kind, {})
    return tuple(replace(slot, concepts=sources.get(slot.key, ())) for slot in slots)


TEMPLATES: dict[ProcedureProcedureType, tuple[Slot, ...]] = {
    "composite": with_sources("composite", COMPOSITE),
    "direct_aesthetic": with_sources("direct_aesthetic", DIRECT_AESTHETIC),
    "veneer_preparation": with_sources("veneer_preparation", VENEER_PREPARATION),
    "veneer_bonding": with_sources("veneer_bonding", VENEER_BONDING),
    "wear_additive": with_sources("wear_additive", WEAR_ADDITIVE),
    "extraction": with_sources("extraction", EXTRACTION),
    "minor_surgery_generic": with_sources("minor_surgery_generic", MINOR_SURGERY_GENERIC),
}

PROCEDURE_LABELS: dict[ProcedureProcedureType, str] = {
    "composite": "restauration composite",
    "direct_aesthetic": "traitement esthétique direct",
    "veneer_preparation": "préparation pour facettes",
    "veneer_bonding": "collage de facettes",
    "wear_additive": "restauration additive sur usures",
    "extraction": "avulsion",
    "minor_surgery_generic": "chirurgie mineure",
}


def template_for(procedure_type: ProcedureProcedureType) -> tuple[Slot, ...]:
    """Modèle du type d'acte ; à défaut, le modèle chirurgical générique (§44)."""
    return TEMPLATES.get(procedure_type, MINOR_SURGERY_GENERIC)


def procedure_label(procedure_type: ProcedureProcedureType) -> str:
    return PROCEDURE_LABELS.get(procedure_type, procedure_type)
