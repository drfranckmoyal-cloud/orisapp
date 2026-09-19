"""Libellés français des concepts cliniques connus, classés par thème.

Ontologie V1 (spec §35–36, §38–44). Un concept absent d'ici n'est jamais
« deviné » : le document le signale comme à rédiger, et le praticien voit tout de
suite ce qui manque au vocabulaire.

La liste lisible par le praticien est `docs/VOCABULAIRE.md`, produite depuis ce
fichier par `scripts/vocabulaire.py` : c'est ce fichier-ci qui fait foi.

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


def c(label: str, value_mode: ValueMode = "hide") -> ConceptLabel:
    return ConceptLabel(label, value_mode)


# Thème -> concept -> libellé. L'ordre des thèmes est celui du compte rendu.
THEMES: dict[str, dict[str, ConceptLabel]] = {
    "Motif et demande du patient": {
        "aesthetic_request": c("demande esthétique", "show"),
        "smile_dissatisfaction": c("insatisfaction du sourire", "show"),
        "tooth_color_complaint": c("couleur des dents jugée insatisfaisante"),
        "broken_tooth_complaint": c("dent cassée signalée par le patient"),
        "lost_restoration_complaint": c("restauration perdue signalée par le patient"),
        "chewing_difficulty": c("gêne à la mastication"),
        "food_impaction": c("tassement alimentaire"),
        "bad_breath": c("mauvaise haleine"),
        "routine_checkup": c("contrôle de routine"),
        "emergency_visit": c("consultation en urgence"),
        "second_opinion": c("deuxième avis demandé"),
        "patient_belief_caries": c("carie"),
    },
    "Symptômes rapportés": {
        "nocturnal_pain": c("douleur nocturne"),
        "spontaneous_pain": c("douleur spontanée"),
        "pain_on_chewing": c("douleur à la mastication"),
        "lingering_pain": c("douleur persistante après stimulus"),
        "radiating_pain": c("douleur irradiée"),
        "throbbing_pain": c("douleur pulsatile"),
        "pain_location": c("douleur localisée"),
        "pain_reproduced": c("douleur reproduite"),
        "cold_sensitivity": c("sensibilité au froid"),
        "heat_sensitivity": c("sensibilité au chaud"),
        "sweet_sensitivity": c("sensibilité au sucré"),
        "pressure_sensitivity": c("sensibilité à la pression"),
        "hypersensitivity": c("hypersensibilité", "show"),
        "gum_bleeding": c("saignement gingival"),
        "gum_pain": c("douleur gingivale"),
        "swelling": c("gonflement"),
        "jaw_pain": c("douleur des mâchoires"),
        "joint_clicking": c("craquement articulaire"),
        "morning_jaw_stiffness": c("raideur matinale des mâchoires"),
        "headache": c("céphalées"),
        "dry_mouth": c("bouche sèche"),
        "taste_disturbance": c("trouble du goût"),
        "paresthesia": c("paresthésie"),
        "perceived_tooth_shortening": c("raccourcissement des dents ressenti"),
    },
    "Examen clinique — dents et restaurations": {
        "caries": c("carie"),
        "secondary_caries": c("carie secondaire"),
        "caries_diagnosis": c("carie"),
        "crack": c("fissure"),
        "enamel_crack": c("fêlure de l’émail"),
        "tooth_fracture": c("fracture dentaire"),
        "cusp_fracture": c("fracture cuspidienne"),
        "fractured_restoration": c("restauration fracturée"),
        "worn_restoration": c("restauration usée"),
        "defective_margin": c("joint défectueux"),
        "marginal_infiltration": c("infiltration marginale"),
        "lost_restoration": c("restauration absente"),
        "missing_tooth": c("dent absente"),
        "retained_root": c("racine résiduelle"),
        "tooth_mobility": c("mobilité dentaire", "statement"),
        "tooth_discoloration": c("dyschromie"),
        "intrinsic_discoloration": c("dyschromie intrinsèque"),
        "extrinsic_stain": c("coloration extrinsèque"),
        "enamel_hypoplasia": c("hypoplasie de l’émail"),
        "white_spot": c("tache blanche"),
        "exposed_dentin": c("dentine exposée"),
        "existing_crown": c("couronne en place"),
        "defective_crown": c("couronne défectueuse"),
        "existing_bridge": c("bridge en place"),
        "existing_veneer": c("facette en place"),
        "removable_denture": c("prothèse amovible en place"),
        "existing_implant": c("implant en place"),
    },
    "Examen clinique — usures et esthétique": {
        "anterior_tooth_wear": c("usure des dents antérieures", "show"),
        "generalized_tooth_wear": c("usure généralisée", "show"),
        "erosion": c("érosion"),
        "attrition": c("attrition"),
        "abrasion": c("abrasion"),
        "abfraction": c("abfraction"),
        "shape_asymmetry": c("asymétrie de forme"),
        "diastema": c("diastème"),
        "smile_line": c("ligne du sourire", "statement"),
        "gummy_smile": c("sourire gingival"),
        "incisal_edge_position": c("position des bords libres", "statement"),
        "tooth_proportion": c("proportions dentaires", "statement"),
        "shade": c("teinte", "statement"),
        "midline_deviation": c("déviation des milieux"),
    },
    "Examen clinique — parodonte, muqueuses, occlusion": {
        "plaque": c("plaque dentaire"),
        "calculus": c("tartre"),
        "gingivitis": c("gingivite"),
        "periodontitis": c("parodontite"),
        "gingival_recession": c("récession gingivale"),
        "bleeding_on_probing": c("saignement au sondage", "statement"),
        "pocket_depth": c("profondeur de poche", "statement"),
        "furcation_involvement": c("atteinte de furcation", "statement"),
        "gingival_inflammation": c("inflammation gingivale"),
        "mucosal_lesion": c("lésion muqueuse", "show"),
        "ulceration": c("ulcération"),
        "occlusal_interference": c("interférence occlusale"),
        "premature_contact": c("contact prématuré"),
        "overjet": c("surplomb", "statement"),
        "overbite": c("recouvrement", "statement"),
        "crossbite": c("occlusion inversée"),
        "open_bite": c("béance"),
        "crowding": c("encombrement"),
    },
    "Examens complémentaires": {
        "additional_assessment": c("examen complémentaire"),
        "diagnostic_workup": c("bilan diagnostique", "show"),
        "periapical_radiograph": c("radiographie rétro-alvéolaire"),
        "bitewing_radiograph": c("radiographie bitewing"),
        "panoramic_radiograph": c("radiographie panoramique"),
        "cone_beam": c("cone beam"),
        "clinical_photographs": c("photographies cliniques"),
        "scan": c("empreinte optique"),
        "vitality_test": c("test de vitalité", "statement"),
        "percussion_test": c("test de percussion", "statement"),
        "palpation_test": c("test de palpation", "statement"),
        "periapical_radiolucency": c("image radioclaire périapicale"),
        "radiographic_bone_loss": c("perte osseuse radiographique", "statement"),
        "radiographic_caries": c("carie visible à la radiographie"),
        "no_radiographic_anomaly": c("absence d’anomalie radiographique"),
    },
    "Analyse, diagnostic et hypothèses": {
        "reversible_pulpitis": c("pulpite réversible"),
        "irreversible_pulpitis": c("pulpite irréversible"),
        "pulp_necrosis": c("nécrose pulpaire"),
        "apical_periodontitis": c("parodontite apicale"),
        "dentin_hypersensitivity": c("hypersensibilité dentinaire"),
        "cracked_tooth_syndrome": c("syndrome de la dent fêlée"),
        "occlusal_overload": c("surcharge occlusale"),
        "bruxism": c("bruxisme"),
        "parafunction": c("parafonction"),
        "gastroesophageal_reflux": c("reflux gastro-œsophagien"),
        "erosive_diet": c("alimentation érosive"),
        "etiology": c("étiologie", "statement"),
        "wear_factor": c("facteur d’usure", "show"),
        "differential_diagnosis": c("diagnostic différentiel", "value_only"),
        "prognosis": c("pronostic", "statement"),
    },
    "Options thérapeutiques et décisions": {
        "treatment_option": c("option thérapeutique", "value_only"),
        "preferred_option": c("option", "value_only"),
        "no_treatment_option": c("surveillance sans traitement"),
        "monitoring": c("surveillance"),
        "whitening": c("éclaircissement"),
        "composite": c("composite", "show"),
        "additive_composites": c("composites additifs"),
        "veneers": c("facettes"),
        "crowns": c("couronnes"),
        "inlay": c("inlay"),
        "onlay": c("onlay"),
        "bridge": c("bridge"),
        "removable_prosthesis": c("prothèse amovible"),
        "implant_option": c("implant"),
        "orthodontic_treatment": c("traitement orthodontique"),
        "occlusal_splint": c("gouttière occlusale"),
        "endodontic_treatment": c("traitement endodontique"),
        "periodontal_treatment": c("traitement parodontal"),
        "scaling": c("détartrage"),
        "root_planing": c("surfaçage radiculaire"),
        "extraction": c("avulsion"),
        "remove_restoration_and_reassess": c("dépose de la restauration et réévaluation"),
        "referral": c("adressage à un confrère", "show"),
        "cost_estimate": c("devis", "statement"),
        "treatment_sequence": c("séquence de traitement", "value_only"),
        "deferred_decision": c("décision différée"),
        "informed_consent": c("consentement éclairé", "statement"),
        "aesthetic_approval": c("validation esthétique", "statement"),
        "preventive_management": c("prise en charge préventive"),
    },
    "Projet esthétique": {
        "mock_up": c("mock-up"),
        "wax_up": c("wax-up"),
        "digital_smile_design": c("projet esthétique numérique"),
        "shade_selection": c("choix de la teinte", "show"),
        "shade_communication": c("communication de la teinte"),
        "mockup_guided_reduction": c("réduction guidée par mock-up"),
    },
    "Actes — restaurations directes": {
        "composite_restoration": c("restauration composite"),
        "additive_composite": c("restauration additive en composite", "show"),
        "isolation": c("isolation du champ opératoire"),
        "cavity_preparation": c("préparation de la cavité"),
        "caries_removal": c("curetage de la carie"),
        "pulp_capping": c("coiffage pulpaire", "show"),
        "cavity_liner": c("fond de cavité", "show"),
        "etching": c("mordançage"),
        "adhesive": c("adhésif", "show"),
        "matrix": c("matrice", "show"),
        "layering": c("stratification"),
        "temporary_restoration": c("restauration provisoire", "show"),
        "finishing_polishing": c("finition et polissage"),
        "finishing_polishing_occlusion": c("finitions, polissage et contrôle occlusal"),
        "finishing_contacts_occlusion": c("finitions, contrôle des contacts et de l’occlusion"),
        "occlusal_adjustment": c("réglage de l’occlusion"),
        "surface": c("face", "statement"),
    },
    "Actes — prothèse et collage": {
        "veneer_preparation": c("préparation pour facettes"),
        "crown_preparation": c("préparation pour couronne"),
        "impression": c("empreinte", "show"),
        "provisionals": c("provisoires"),
        "provisionals_removal": c("dépose des provisoires"),
        "try_in": c("essayage"),
        "sandblasting": c("sablage"),
        "veneer_bonding": c("collage des facettes"),
        "cementation": c("scellement", "show"),
        "bonding_material": c("matériau de collage", "show"),
        "occlusal_check": c("contrôle de l’occlusion"),
    },
    "Actes — chirurgie et anesthésie": {
        "local_anesthesia": c("anesthésie locale"),
        "surgical_approach": c("abord chirurgical", "statement"),
        "root_sectioning": c("séparation radiculaire"),
        "alveolar_curettage": c("curetage alvéolaire"),
        "socket_preservation": c("préservation alvéolaire"),
        "hemostasis": c("hémostase", "statement"),
        "sutures": c("sutures", "statement"),
        "suture_removal": c("dépose des sutures"),
        "complication": c("complication", "statement"),
    },
    "Informations données au patient": {
        "oral_hygiene_instructions": c("conseils d’hygiène bucco-dentaire"),
        "brushing_technique": c("technique de brossage"),
        "interdental_cleaning": c("nettoyage interdentaire"),
        "fluoride_application": c("application de fluor"),
        "desensitizing_agent": c("produit désensibilisant", "show"),
        "dietary_advice": c("conseils alimentaires", "show"),
        "acid_exposure_advice": c("conseils sur l’exposition aux acides"),
        "smoking_advice": c("conseils sur le tabac"),
        "splint_wear_instructions": c("consignes de port de la gouttière"),
        "risks_explained": c("risques expliqués", "show"),
        "alternatives_explained": c("alternatives expliquées", "show"),
        "cost_information": c("information sur le coût", "show"),
        "postoperative_instructions": c("consignes postopératoires", "statement"),
    },
    "Antécédents, traitements et terrain": {
        "medical_history": c("antécédents médicaux", "show"),
        "allergy": c("allergie", "show"),
        "anticoagulant_treatment": c("traitement anticoagulant", "show"),
        "bisphosphonates": c("bisphosphonates", "show"),
        "diabetes": c("diabète"),
        "cardiac_condition": c("antécédent cardiaque", "show"),
        "radiotherapy": c("antécédent de radiothérapie"),
        "pregnancy": c("grossesse"),
        "smoking": c("tabagisme", "statement"),
        "previous_dental_treatment": c("traitement dentaire antérieur", "show"),
        "dental_anxiety": c("anxiété dentaire"),
    },
    "Suite et contrôle": {
        "next_visit": c("prochaine séance", "statement"),
        "recall": c("contrôle périodique", "statement"),
        "reassessment": c("réévaluation", "statement"),
        "healing_check": c("contrôle de cicatrisation"),
        "periodontal_maintenance": c("maintenance parodontale"),
        "emergency_instructions": c("consignes en cas d’urgence"),
    },
}

# Vue à plat : c'est elle que lisent le rédacteur de documents et l'invite du modèle.
CONCEPTS: dict[str, ConceptLabel] = {
    concept: label for group in THEMES.values() for concept, label in group.items()
}
THEME_OF: dict[str, str] = {concept: theme for theme, group in THEMES.items() for concept in group}

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
