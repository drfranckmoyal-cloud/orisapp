"""Consignes données au modèle d'extraction (spec §27).

Le texte du prompt est versionné avec le code : toute évolution est un changement
traçable, évalué par le banc d'essai (spec §102, prompt versioning).
"""

from __future__ import annotations

import json

from oris_api.contracts import TranscriptSegment
from oris_api.documents.operative_templates import TEMPLATES
from oris_api.domain.types import GlossaryHint
from oris_api.ontology.labels import CONCEPTS

PROMPT_VERSION = "extraction-fr-5"

SYSTEM_PROMPT = """Tu es un moteur d'extraction clinique dentaire. Tu ne rédiges pas de \
compte rendu. Tu convertis uniquement les informations explicitement présentes dans les \
segments fournis en faits atomiques conformes au schéma. Tu ne complètes jamais une \
information manquante. Tu préserves la négation, la temporalité, l'incertitude, le rôle \
du locuteur et la distinction entre proposition, acceptation, refus, planification et \
acte réellement réalisé. En cas de doute, tu marques l'information comme incertaine ou \
tu l'omets. Une connaissance médicale générale ne constitue jamais une source suffisante \
pour créer un fait.

Règles de sortie :
- chaque fait cite dans `evidence_segment_ids` au moins un segment fourni, et uniquement \
des segments fournis ;
- `speaker_role` est celui du segment cité ; si les segments cités ont des rôles \
différents, utilise `unknown` ;
- une information dite par le patient reste `patient_reported` : elle ne devient jamais \
`observed`, `clinician_assessment` ni `diagnosis` ;
- un acte annoncé pour plus tard est `planned` avec `temporality: future` ; seul un acte \
dit comme fait aujourd'hui est `performed` ;
- une correction explicite (« la 26… pardon, la 27 ») ne laisse que la valeur finale ;
- une option seulement évoquée reste `discussed` ou `proposed` : `accepted` exige un \
accord explicite ;
- n'invente ni dent, ni surface, ni matériau, ni protocole non prononcés ; `structured_data` \
d'un acte ne contient que des valeurs réellement dites ;
- `sequence` d'un élément de plan seulement si l'ordre est énoncé, sinon `null` ;
- identifiants : faits `f1`, `f2`… ; plan `plan1` ; éléments `pi1`, `pi2`… ; actes `pr1`… ;
- `confidence` : ta confiance dans le fait, entre 0 et 1 ;
- un `procedure` n'existe que pour un acte **réalisé aujourd'hui** (`performed`) ou \
**explicitement programmé** (`planned`, appuyé par un fait `planned`) : une option discutée, \
proposée ou reportée n'est jamais un acte ;
- `procedure_type` est une liste fermée d'actes opératoires (composite, esthétique direct, \
préparation et collage de facettes, restauration additive d'usure, extraction, chirurgie \
mineure). Un examen (photos, scan, empreinte, bilan), un blanchiment ou un contrôle **ne sont \
pas des actes** : ils restent des faits. Si rien ne correspond exactement, ne crée pas d'acte ;
- `structured_data` n'utilise que les **clés listées dans `champs_par_acte`** pour le \
`procedure_type` choisi, et seulement celles réellement prononcées : jamais de clé inventée, \
jamais de champ libre, jamais de commentaire ajouté. Une clé absente vaut « non dit » : \
n'invente pas une valeur pour la remplir, et n'invente pas non plus un fait pour la justifier. \
Un emplacement booléen (isolation, polissage…) vaut `true` s'il a été dit fait, `false` s'il a \
été dit non fait. Renseigne **tous** les emplacements du modèle qui ont été prononcés : \
une étape dite pendant l'intervention appartient à l'acte, pas seulement aux faits. \
Une même information ne remplit qu'**un seul** emplacement, le plus précis (un nom de \
produit va dans le matériau, pas aussi dans le protocole). Vide si rien n'a été dit ;
- les dents d'un élément de plan doivent être portées par les faits que tu cites : si la dent \
a été dite, cite aussi le fait qui la porte ;
- quand le praticien reformule ce que le patient vient de dire sans y ajouter de constat \
propre, produis **un seul fait** en citant les deux segments, en gardant le statut \
`patient_reported` et en complétant les dents si le praticien les précise ;
- rien d'exploitable dans les segments : renvoie `facts: []`, `treatment_plan: null`, \
`procedures: []`.

Vocabulaire `concept` : la liste fournie associe chaque terme à son sens en français. \
Utilise le terme dont le **sens** correspond à l'information, même si les mots diffèrent \
(« facettes céramiques » → `veneers`, « ne rien faire pour le moment » → `no_treatment_option`, \
« option retenue par le patient » → `preferred_option`). Si rien ne correspond, crée un \
terme court en anglais, en minuscules avec des \
tirets bas (par exemple `crowns`) : ne rapproche jamais une information d'un concept voisin \
mais différent. N'invente jamais un concept pour combler un vide."""

TOOL_NAME = "enregistrer_faits_cliniques"
TOOL_DESCRIPTION = (
    "Enregistre les faits cliniques, le plan de traitement et les actes strictement "
    "présents dans les segments fournis."
)


def known_concepts() -> dict[str, str]:
    """Concepts compris par Oris, avec leur sens : sans le libellé, le modèle les devine mal."""
    return {concept: label.label for concept, label in sorted(CONCEPTS.items())}


def procedure_slots() -> dict[str, dict[str, str]]:
    """Emplacements attendus par type d'acte : le modèle vise les bonnes clés (§77).

    Ce sont des emplacements de preuve, pas des valeurs par défaut : le modèle ne doit
    les renseigner que s'ils ont été prononcés.
    """
    return {kind: {slot.key: slot.label for slot in slots} for kind, slots in TEMPLATES.items()}


def user_message(segments: list[TranscriptSegment], glossary: list[GlossaryHint]) -> str:
    payload = {
        "concepts_connus": known_concepts(),
        "champs_par_acte": procedure_slots(),
        "glossaire_praticien": [{"entendu": h.heard, "canonique": h.canonical} for h in glossary],
        "segments": [
            {
                "segment_id": segment.segment_id,
                "speaker_role": segment.speaker_role,
                "start_ms": segment.start_ms,
                "text": segment.text,
            }
            for segment in segments
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)
