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

import re
from collections.abc import Iterable
from dataclasses import dataclass, field

from oris_api.contracts import ClinicalEncounter, ClinicalFact, Procedure, TreatmentPlanItem
from oris_api.documents.operative_templates import (
    SECTIONS,
    Slot,
    procedure_label,
    template_for,
)
from oris_api.domain.types import Claim, GeneratedDocument
from oris_api.ontology.labels import label_for, translate_value

LIMITS_SECTION = "Limites du compte rendu"
# Préfixes qui ne font que répéter l'intitulé de la section : en mode concis, ils
# disparaissent. Rien d'autre ne disparaît : aucun fait, aucune nuance.
REDUNDANT_PREFIXES = {
    "Symptômes rapportés": ("Rapporté par le patient : ",),
    "Examen clinique": ("Constaté : ",),
    "Options thérapeutiques discutées": ("Option discutée : ",),
    # Rubriques du modèle du Dr Moyal : le motif est ce que le patient dit, la
    # proposition ce que le praticien propose.
    "Motif de la consultation": ("Rapporté par le patient : ",),
    "Proposition thérapeutique": ("Option discutée : ", "Proposé : "),
}
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


@dataclass(frozen=True)
class Style:
    """Préférences de forme du praticien. Elles ne changent jamais le fond."""

    length: str = "standard"
    terminology: dict[str, str] = field(default_factory=dict)

    def label_of(self, concept: str, default: str) -> str:
        return self.terminology.get(concept, default)


DEFAULT_STYLE = Style()


def fact_phrase(fact: ClinicalFact, style: Style = DEFAULT_STYLE) -> str | None:
    """Groupe nominal du fait (libellé, valeur dite, dents), ou None si concept inconnu."""
    known = label_for(fact.concept, fact.category)
    if known is None:
        return None
    label = style.label_of(fact.concept, known.label)
    value = translate_value(fact.value)
    teeth = teeth_suffix(fact.teeth)
    match known.value_mode:
        case "value_only":
            return f"{value or label}{teeth}"
        case "show" if value and value != label:
            return f"{label} : {value}{teeth}"
        case _:
            return f"{label}{teeth}"


def shorten(section: str, text: str) -> str:
    """Retire un préfixe qui ne fait que répéter le titre de la section."""
    for prefix in REDUNDANT_PREFIXES.get(section, ()):
        if text.startswith(prefix):
            return capitalize(text[len(prefix) :])
    return text


def fact_sentence(fact: ClinicalFact, style: Style = DEFAULT_STYLE) -> str:
    known = label_for(fact.concept, fact.category)
    phrase = fact_phrase(fact, style)
    if known is None or phrase is None:
        return f"{UNRENDERED_PREFIX} : élément « {fact.concept} » non reconnu par Oris."
    absent = fact.assertion == "absent"
    unsure = fact.assertion == "uncertain" or fact.certainty in {"possible", "probable"}
    status = fact.clinical_status

    label = style.label_of(fact.concept, known.label)
    if known.value_mode == "statement":
        value = translate_value(fact.value) or ("non" if absent else "oui")
        return f"{capitalize(label)}{teeth_suffix(fact.teeth)} : {value}."

    if fact.category == "medication":
        if absent:
            detail = translate_value(fact.value)
            suffix = f" ({detail})" if detail and detail != label else ""
            return f"{capitalize(label)} : n’est plus pris actuellement{suffix}."
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


# --- Compte rendu de consultation, modèle du Dr Moyal (docs/MODELES_CR.md) ------------

#: Rubriques et ordre arrêtés avec le praticien le 21/09/2026 (décision D, D023).
RUBRIQUES_CONSULTATION = (
    "Motif de la consultation",
    "Examen clinique",
    "Diagnostic / analyse",
    "Proposition thérapeutique",
    "Informations données au patient",
    "Actes réalisés",
    "Suite de la prise en charge",
    "Points d’attention / coordination",
)
MOTIF, EXAMEN, DIAGNOSTIC, PROPOSITION, INFORMATIONS, ACTES, SUITE, ATTENTION = (
    RUBRIQUES_CONSULTATION
)

#: En dessous, la valeur n'est qu'un libellé (« douleur nocturne ») : elle ne porte pas
#: seule la négation ou le statut, et la formulation par axes (plus haut) reste la règle.
MOTS_MIN_PHRASE = 4

NEGATION = re.compile(
    r"\b(pas|non|aucune?|absence|absente?s?|sans|ni|jamais|impossib\w*|refus\w*|"
    r"écart\w*|n[’']|bon état|normal\w*|sain\w*|suffisant\w*|respecté\w*)",
    re.IGNORECASE,
)
INCERTITUDE = re.compile(
    r"\b(possible\w*|peut[- ]être|probable\w*|suspicion|suspect\w*|incertain\w*|"
    r"doute\w*|semble\w*|évoqu\w*|hypoth\w*|potentiel\w*|à confirmer|éventuel\w*)",
    re.IGNORECASE,
)
PATIENT = re.compile(
    r"\b(patiente?|se plaint|rapporte|signale|souhait\w*|dit|décrit|ressent)\b", re.IGNORECASE
)
ANTERIEUR = re.compile(r"\b(antérieur\w*|déjà|précédemment|auparavant|il y a)\b", re.IGNORECASE)
INFORMATION = re.compile(r"^(information|informé|informée|explication|expliqué)", re.IGNORECASE)
DENT_ECRITE = re.compile(r"(?<!\d)([1-4][1-8]|[5-8][1-5])(?!\d)")

#: Préfixes dictés qui ne font que répéter le titre de la rubrique.
PREFIXES_DICTES = re.compile(
    r"^(proposition thérapeutique|diagnostic( / analyse)?|information(s)? (données au )?patient|"
    r"motif( de (la )?consultation)?|examen clinique|point(s)? d[’']attention|"
    r"suite de la prise en charge)\s*:\s*",
    re.IGNORECASE,
)
SUFFIXE_MOTIF = re.compile(r",\s*motif de (la )?consultation\s*$", re.IGNORECASE)


def rubrique_de(fact: ClinicalFact) -> str:
    """Où va un fait. Décisions du 21/09/2026 : antécédents dans « Points d'attention »,
    radios dans « Examen clinique », options écartées ou refusées hors de la proposition."""
    category, status, concept = fact.category, fact.clinical_status, fact.concept
    value = fact.value if isinstance(fact.value, str) else ""
    if concept == "referral" or category in {"chief_complaint", "symptom"}:
        return MOTIF
    if category in {"clinical_finding", "radiographic_finding"}:
        return EXAMEN
    if category in {"assessment", "diagnosis"}:
        return DIAGNOSTIC
    if (
        category == "patient_information"
        or concept == "informed_consent"
        or INFORMATION.match(value.strip())
    ):
        return INFORMATIONS
    if concept == "cost_estimate" or category == "follow_up":
        return SUITE
    if category in {"history", "medication"}:
        return ATTENTION
    if category in {"treatment_option", "treatment_decision", "material", "procedure"}:
        if status == "performed" and fact.assertion != "absent":
            return ACTES
        if status in {"planned", "deferred"}:
            return SUITE
        if fact.assertion != "present" or status == "refused":
            return ATTENTION
        return PROPOSITION
    return ATTENTION


def phrase_dictee(fact: ClinicalFact) -> str | None:
    """La valeur dite, nettoyée, si elle forme une phrase ; sinon None.

    Un traitement médicamenteux garde sa formulation dédiée (« n'est plus pris
    actuellement ») ; une valeur codée (traduite par l'ontologie) n'est pas une phrase dite.
    """
    if not isinstance(fact.value, str) or fact.category == "medication":
        return None
    if translate_value(fact.value) != fact.value:
        return None
    texte = SUFFIXE_MOTIF.sub("", PREFIXES_DICTES.sub("", fact.value.strip())).strip(" .;")
    if len(texte.split()) < MOTS_MIN_PHRASE:
        return None
    return capitalize(texte)


def negation_ecrite(texte: str) -> bool:
    """La phrase dit-elle une absence ? Sert au validateur pour les faits niés."""
    return NEGATION.search(texte) is not None


def phrase_redigee(fact: ClinicalFact, style: Style = DEFAULT_STYLE) -> str:
    """Une phrase de compte rendu pour ce fait.

    La phrase reprend les mots dits : c'est ce qui garde le sens (« agénésie », « gouttière
    conformatrice »), là où un libellé de liste l'appauvrissait. Les axes du fait ne sont
    ajoutés que quand les mots dits ne les portent pas déjà. Une valeur trop courte pour
    faire une phrase garde la formulation par axes, éprouvée par les tests critiques.
    """
    dite = phrase_dictee(fact)
    if dite is None:
        return fact_sentence(fact, style)

    texte = dite
    if not DENT_ECRITE.search(texte) and fact.teeth:
        texte += teeth_suffix(fact.teeth)
    status = fact.clinical_status

    incertain = fact.assertion == "uncertain" or fact.certainty in {"possible", "probable"}
    if incertain and not INCERTITUDE.search(texte):
        texte += ", non confirmé"
    if status == "patient_reported" and not PATIENT.search(texte):
        texte = f"Selon le patient, {texte[:1].lower()}{texte[1:]}"
    anterieur = fact.temporality == "past" and status in {"discussed", "proposed"}
    if anterieur and not ANTERIEUR.search(texte):
        texte = f"Évoqué antérieurement : {texte[:1].lower()}{texte[1:]}"
    if status == "refused" and not NEGATION.search(texte):
        texte = f"Refusé : {texte[:1].lower()}{texte[1:]}"
    elif (
        fact.assertion == "absent"
        and status in {"discussed", "proposed"}
        and not NEGATION.search(texte)
    ):
        texte = f"Écarté : {texte[:1].lower()}{texte[1:]}"
    return f"{texte}."


def _cle(texte: str) -> str:
    return re.sub(r"[^a-z0-9àâäéèêëîïôöùûüç]+", " ", texte.lower()).strip()


def render_consultation_note(
    encounter: ClinicalEncounter, style: Style = DEFAULT_STYLE
) -> GeneratedDocument:
    """Compte rendu de consultation dans les rubriques du modèle, avec les mots dits.

    Une rubrique sans contenu n'existe pas. Deux faits qui disent la même chose dans la
    même rubrique (« 2 bridges cantilever » et le détail des deux bridges) ne font
    qu'une phrase, la plus complète, qui cite les deux faits.
    """
    par_rubrique: dict[str, list[Claim]] = {rubrique: [] for rubrique in RUBRIQUES_CONSULTATION}
    for fact in encounter.facts:
        rubrique = rubrique_de(fact)
        texte = phrase_redigee(fact, style)
        if style.length == "concise":
            texte = shorten(rubrique, texte)
        claims = par_rubrique[rubrique]
        # Comparer ce qui a été dit, pas la formule autour : « 2 bridges cantilever » est
        # contenu dans le détail des deux bridges, même rédigé « Proposé : … ».
        dit = fact.value if isinstance(fact.value, str) else ""
        dit = SUFFIXE_MOTIF.sub("", PREFIXES_DICTES.sub("", dit.strip()))
        cle = _cle(dit) if len(_cle(dit).split()) >= 2 else _cle(texte)
        doublon = next(
            (
                i
                for i, claim in enumerate(claims)
                if cle and (cle in _cle(claim.text) or _cle(claim.text) in cle)
            ),
            None,
        )
        if doublon is not None:
            garde = claims[doublon]
            plus_long = texte if len(texte) > len(garde.text) else garde.text
            claims[doublon] = Claim(
                rubrique,
                plus_long,
                fact_ids=(*garde.fact_ids, fact.fact_id),
                warning_codes=garde.warning_codes,
            )
            continue
        claims.append(Claim(rubrique, texte, fact_ids=(fact.fact_id,)))
    claims = limits_claims(encounter)
    for rubrique in RUBRIQUES_CONSULTATION:
        claims += par_rubrique[rubrique]
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


def slot_sentence(slot: Slot, value: object) -> str | None:
    """Une phrase pour un emplacement **renseigné**. Rien d'autre n'est écrit.

    Un emplacement absent renvoie `None` : il n'existe pas dans le document (§37).
    Un emplacement explicitement nié (« pas de sutures ») s'écrit tel quel : c'est une
    information, pas un vide.
    """
    if value is None or value == "" or value == []:
        return None
    if slot.kind == "flag":
        if value is True:
            return f"Réalisé : {slot.label}."
        if value is False:
            return f"{capitalize(slot.label)} : non."
        # Un emplacement attendu « oui/non » peut arriver précisé (« provisoires
        # réalisés le jour même ») : la précision a été dite, elle n'est pas jetée.
        written = translate_value(value)
        return f"{capitalize(slot.label)} : {written}." if written else None
    written = translate_value(value)
    if written is None:
        return None
    return f"{capitalize(slot.label)} : {written}."


def missing_important_slots(
    procedure: Procedure, facts: list[ClinicalFact] | None = None
) -> list[Slot]:
    """Emplacements importants restés vides : ils alertent, ils ne se remplissent pas (§45).

    Seul un acte réalisé est concerné : un acte seulement prévu n'a ni matériau ni
    hémostase à documenter.
    """
    if procedure.status != "performed":
        return []
    return [
        slot
        for slot in template_for(procedure.procedure_type)
        if slot.important and slot_value(slot, procedure, facts or []) is None
    ]


def fact_fills(slot: Slot, procedure: Procedure, facts: list[ClinicalFact]) -> ClinicalFact | None:
    """Fait qui renseigne cet emplacement : dit pendant l'acte, sur les mêmes dents.

    Rien n'est deviné : le fait existe déjà, avec sa preuve. Le document ne fait que le
    placer dans l'emplacement du modèle, et cite ce fait.
    """
    for fact in facts:
        if fact.concept not in slot.concepts or fact.clinical_status != procedure.status:
            continue
        if fact.teeth and procedure.teeth and not set(fact.teeth) & set(procedure.teeth):
            continue
        return fact
    return None


def slot_value(
    slot: Slot, procedure: Procedure, facts: list[ClinicalFact]
) -> tuple[object, tuple[str, ...]] | None:
    """Valeur d'un emplacement et preuves qui l'appuient, ou rien s'il n'a pas été dit."""
    spoken = procedure.structured_data.get(slot.key)
    if spoken not in (None, "", []):
        return spoken, tuple(procedure.evidence_fact_ids)
    fact = fact_fills(slot, procedure, facts)
    if fact is None:
        return None
    if slot.kind == "flag":
        return fact.assertion == "present", (fact.fact_id,)
    value = fact.value if isinstance(fact.value, str) and fact.value.strip() else None
    return (value, (fact.fact_id,)) if value else None


def procedure_claims(procedure: Procedure, facts: list[ClinicalFact] | None = None) -> list[Claim]:
    """Les phrases d'un acte, dans l'ordre des sections du modèle."""
    facts = facts or []
    evidence = tuple(procedure.evidence_fact_ids)
    label = procedure_label(procedure.procedure_type)
    teeth = teeth_suffix(procedure.teeth)
    claims = [
        Claim("Acte réalisé", f"{capitalize(label)}{teeth}.", fact_ids=evidence)
        if procedure.status == "performed"
        else Claim("Acte prévu", f"{capitalize(label)}{teeth} — prévu.", fact_ids=evidence)
    ]
    slots = template_for(procedure.procedure_type)
    for section in SECTIONS:
        for slot in (s for s in slots if s.section == section):
            found = slot_value(slot, procedure, facts)
            if found is None:
                continue
            sentence = slot_sentence(slot, found[0])
            if sentence is not None:
                claims.append(Claim(section, sentence, fact_ids=found[1]))
    return claims


def render_operative_note(encounter: ClinicalEncounter) -> GeneratedDocument:
    """Compte rendu de soins : un bloc par acte, rien que ce qui a été dit (§37–45)."""
    claims = limits_claims(encounter)
    for procedure in encounter.procedures:
        if procedure.status == "cancelled":
            continue
        claims += procedure_claims(procedure, list(encounter.facts))
    return GeneratedDocument("operative_note", render_content(claims), tuple(claims))
