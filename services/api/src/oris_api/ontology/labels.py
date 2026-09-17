"""Libellés français des concepts cliniques connus.

Amorce de l'ontologie V1 (spec §35–36, §38–44) couvrant le corpus synthétique.
Un concept absent d'ici n'est jamais « deviné » : le document le signale comme
à rédiger.

Modes de restitution de la valeur :
- `hide` : la valeur ne fait que répéter le statut (« present », « performed ») ;
- `show` : la valeur est un texte dit (nom de matériau, demande du patient) ;
- `value_only` : la valeur est l'élément lui-même (intitulé d'une option) ;
- `statement` : « libellé : valeur » sans préfixe de statut (hémostase : obtenue).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ValueMode = Literal["hide", "show", "value_only", "statement"]


@dataclass(frozen=True)
class ConceptLabel:
    label: str
    value_mode: ValueMode = "hide"


CONCEPTS: dict[str, ConceptLabel] = {
    # Consultation esthétique
    "aesthetic_request": ConceptLabel("demande esthétique", "show"),
    "shape_asymmetry": ConceptLabel("asymétrie de forme"),
    "treatment_option": ConceptLabel("option thérapeutique", "value_only"),
    "no_treatment_option": ConceptLabel("surveillance sans traitement"),
    "preferred_option": ConceptLabel("option", "value_only"),
    "diagnostic_workup": ConceptLabel("bilan diagnostique", "show"),
    "aesthetic_approval": ConceptLabel("validation esthétique", "statement"),
    "veneers": ConceptLabel("facettes"),
    "additive_composites": ConceptLabel("composites additifs"),
    "clinical_photographs": ConceptLabel("photographies cliniques"),
    # Usures
    "perceived_tooth_shortening": ConceptLabel("raccourcissement des dents ressenti"),
    "anterior_tooth_wear": ConceptLabel("usure des dents antérieures", "show"),
    "wear_factor": ConceptLabel("facteur d’usure", "show"),
    "etiology": ConceptLabel("étiologie", "statement"),
    "preventive_management": ConceptLabel("prise en charge préventive"),
    "additive_composite": ConceptLabel("restauration additive en composite", "show"),
    "hypersensitivity": ConceptLabel("hypersensibilité", "show"),
    # Actes et matériaux
    "composite_restoration": ConceptLabel("restauration composite"),
    "isolation": ConceptLabel("isolation du champ opératoire"),
    "surface": ConceptLabel("face", "statement"),
    "adhesive": ConceptLabel("adhésif", "show"),
    "composite": ConceptLabel("composite", "show"),
    "bonding_material": ConceptLabel("matériau de collage", "show"),
    "finishing_polishing": ConceptLabel("finition et polissage"),
    "finishing_polishing_occlusion": ConceptLabel("finitions, polissage et contrôle occlusal"),
    "finishing_contacts_occlusion": ConceptLabel(
        "finitions, contrôle des contacts et de l’occlusion"
    ),
    "complication": ConceptLabel("complication", "statement"),
    "veneer_preparation": ConceptLabel("préparation pour facettes"),
    "mockup_guided_reduction": ConceptLabel("réduction guidée par mock-up"),
    "scan": ConceptLabel("empreinte optique"),
    "shade_communication": ConceptLabel("communication de la teinte"),
    "provisionals": ConceptLabel("provisoires"),
    "veneer_bonding": ConceptLabel("collage des facettes"),
    "next_visit": ConceptLabel("prochaine séance", "statement"),
    "extraction": ConceptLabel("avulsion"),
    "local_anesthesia": ConceptLabel("anesthésie locale"),
    "surgical_approach": ConceptLabel("abord chirurgical", "statement"),
    "hemostasis": ConceptLabel("hémostase", "statement"),
    "sutures": ConceptLabel("sutures", "statement"),
    "postoperative_instructions": ConceptLabel("consignes postopératoires", "statement"),
    # Cas critiques
    "fractured_restoration": ConceptLabel("restauration fracturée"),
    "remove_restoration_and_reassess": ConceptLabel("dépose de la restauration et réévaluation"),
    "nocturnal_pain": ConceptLabel("douleur nocturne"),
    "cold_sensitivity": ConceptLabel("sensibilité au froid"),
    "crack": ConceptLabel("fissure"),
    "additional_assessment": ConceptLabel("examen complémentaire"),
    "patient_belief_caries": ConceptLabel("carie"),
    "caries_diagnosis": ConceptLabel("carie"),
    "pain_location": ConceptLabel("douleur localisée"),
    "pain_reproduced": ConceptLabel("douleur reproduite"),
}

# Valeurs anglaises normalisées du corpus -> français. Les textes dits en français
# (noms de matériaux, demandes) passent tels quels.
VALUES: dict[str, str] = {
    "incisal length loss": "perte de longueur incisale",
    "not concluded": "non conclue",
    "possible after analysis": "envisageable après analyse",
    "photos and scan first": "photos et scan au préalable",
    "cold sensitivity": "au froid",
    "none reported": "aucune signalée",
    "try-in and bonding": "essayage et collage",
    "shape and color approved": "forme et teinte validées",
    "flap and osteotomy": "lambeau et ostéotomie",
    "simple extraction": "extraction simple",
    "obtained": "obtenue",
    "placed": "mises en place",
    "not required": "non nécessaires",
    "given": "données",
    "stopped six months ago": "arrêté depuis six mois",
    "previous medication": "traitement antérieur",
    "M": "mésiale",
    "D": "distale",
    "O": "occlusale",
    "V": "vestibulaire",
    "B": "buccale",
    "L": "linguale",
    "P": "palatine",
    "I": "incisale",
    "C": "cervicale",
}

# Catégories dont le concept est lui-même un nom propre (médicament).
NAMED_CONCEPT_CATEGORIES = frozenset({"medication"})


def label_for(concept: str, category: str) -> ConceptLabel | None:
    known = CONCEPTS.get(concept)
    if known is not None:
        return known
    if category in NAMED_CONCEPT_CATEGORIES or (category == "history" and concept[:1].isupper()):
        return ConceptLabel(concept, "show")
    return None


def translate_value(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return VALUES.get(value, value)
