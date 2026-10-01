"""Attribution des rôles aux locuteurs détectés par le STT (spec §15).

Principe : une erreur de rôle est dangereuse (une impression du patient deviendrait
un constat du praticien). La règle cherche donc des **tournures propres à chaque rôle**
(« je note », « je propose », « à l'examen » ; « j'ai mal », « je préfère », « je pense
que ») plutôt qu'un vocabulaire commun, et laisse `unknown` dès que ce n'est pas net.
Le praticien pourra corriger un rôle ; l'extraction ne se fie jamais à un rôle inconnu.

Ces règles suffisent sur un enregistrement propre (banc d'essai : 84 % de rôles justes),
pas sur une vraie consultation au fauteuil, où elles laissent presque tout en `unknown`
(constaté sur ZEKRI et BENSOUSSAN, 26/09/2026). Quand elles ne tranchent pas, le
pipeline demande son avis au modèle de langue (`llm/speaker_roles.py`) — qui ne voit que
des extraits de paroles, ne produit qu'un rôle par voix, et n'a pas le droit de créer un
fait. Ce qui reste douteux reste `unknown`, et la consultation porte son alerte.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass

from oris_api.contracts import TranscriptSegment
from oris_api.ontology.stt_glossary import DENTAL_GLOSSARY_FR

PRACTITIONER_CUES = tuple(
    re.compile(pattern)
    for pattern in (
        r"\bje (?:vous )?propose\b",
        r"\bje note\b",
        r"\bje constate\b",
        r"\bje retiens\b",
        r"\bon retient\b",
        r"\bje (?:ne )?vois\b",
        r"\bà l'examen\b",
        r"\bon va\b",
        r"\bon a (?:fait|réalisé|discuté|posé|retenu|mis)\b",
        r"\bon (?:fera|commence|termine|complète)\b",
        r"\bréalisée?s?\b",
        r"\bmise? en place\b",
        r"\bpas de complication\b",
        r"\b(?:sur|la|les|de) (?:1[1-8]|2[1-8]|3[1-8]|4[1-8])\b",
        r"\bvous prenez\b",
        r"\bdocument(?:er|ons)\b",
    )
)
PATIENT_CUES = tuple(
    re.compile(pattern)
    for pattern in (
        r"\bje (?:voudrais|veux|préfère|souhaite(?:rais)?)\b",
        r"\bj'ai (?:(?:un peu|très|vraiment|souvent|toujours) )?"
        r"(?:mal|peur|l'impression|une douleur|des douleurs)\b",
        r"\b(?:ça|cela) me (?:fait|gêne)\b",
        r"\bme fait mal\b",
        r"\bje (?:pense|crois) que\b",
        r"\bmes dents\b",
        r"\best-ce que\b",
        r"\bje (?:ne )?(?:le |la |les )?prends\b",
        r"\bdocteur\b",
        r"\bd'accord\b",
        r"\bmerci\b",
    )
)
GLOSSARY_WORDS = {term.lower() for term in DENTAL_GLOSSARY_FR}
MIN_PRACTITIONER_HITS = 2


@dataclass(frozen=True)
class SpeakerCues:
    practitioner: int
    patient: int


@dataclass(frozen=True)
class Voix:
    """Une voix séparée par la transcription, résumée pour décider de son rôle.

    Pas de texte intégral : quelques extraits suffisent à reconnaître qui soigne et qui
    est soigné, et moins on sort de paroles, mieux c'est.
    """

    label: str
    segments: int
    duree_ms: int
    part: float
    premier_ms: int
    extraits: list[str]
    indices: SpeakerCues


@dataclass(frozen=True)
class RoleAssignment:
    roles: dict[str, str]
    confident: bool


def count_cues(texts: list[str]) -> SpeakerCues:
    text = " ".join(texts).lower().replace("’", "'")
    practitioner = sum(len(p.findall(text)) for p in PRACTITIONER_CUES)
    practitioner += sum(1 for term in GLOSSARY_WORDS if term in text)
    patient = sum(len(p.findall(text)) for p in PATIENT_CUES)
    return SpeakerCues(practitioner, patient)


def looks_like_practitioner(cues: SpeakerCues) -> bool:
    return cues.practitioner >= MIN_PRACTITIONER_HITS and cues.practitioner > 2 * cues.patient


def assign_roles(
    segments: list[TranscriptSegment], speaker_labels: dict[str, str]
) -> RoleAssignment:
    by_label: dict[str, list[str]] = defaultdict(list)
    for segment in segments:
        label = speaker_labels.get(segment.segment_id)
        if label is not None:
            by_label[label].append(segment.text)
    cues = {label: count_cues(texts) for label, texts in by_label.items()}
    candidates = [label for label, c in cues.items() if looks_like_practitioner(c)]
    # Un seul locuteur à profil de praticien, sinon on ne tranche pas.
    if len(candidates) != 1:
        return RoleAssignment({}, confident=False)
    practitioner = candidates[0]
    roles = {practitioner: "practitioner"}
    others = [label for label in by_label if label != practitioner]
    if len(others) == 1:
        other = cues[others[0]]
        # Patient seulement s'il parle comme un patient et pas comme un praticien.
        if other.patient >= 1 and other.patient >= other.practitioner:
            roles[others[0]] = "patient"
    return RoleAssignment(roles, confident=True)


def role_from_own_words(text: str) -> str:
    """Rôle déduit d'un seul passage. `unknown` dès que ce n'est pas net."""
    cues = count_cues([text])
    if looks_like_practitioner(cues):
        return "practitioner"
    if cues.patient >= 1 and cues.patient > cues.practitioner:
        return "patient"
    return "unknown"


def apply_roles(
    segments: list[TranscriptSegment], speaker_labels: dict[str, str]
) -> list[TranscriptSegment]:
    # Une seule voix pour toute la consultation, ce n'est pas « une seule personne » :
    # c'est l'absence de séparation (observé sur Deepgram). Donner le même rôle à tout
    # le monde ferait passer une parole du patient pour un constat du praticien
    # (invariant 5) ; chaque passage est alors jugé sur ses propres mots, et reste
    # `unknown` s'il n'a rien de décisif — la consultation porte alors une alerte.
    if len({speaker_labels.get(s.segment_id) for s in segments} - {None}) <= 1:
        return [
            segment.model_copy(update={"speaker_role": role_from_own_words(segment.text)})
            for segment in segments
        ]
    assignment = assign_roles(segments, speaker_labels)
    return [
        segment.model_copy(
            update={
                "speaker_role": assignment.roles.get(
                    speaker_labels.get(segment.segment_id, ""), "unknown"
                )
            }
        )
        for segment in segments
    ]


MAX_EXTRAITS = 8
LONGUEUR_EXTRAIT = 240


@dataclass(frozen=True)
class Parole:
    """Un passage de la consultation, tel qu'il sera soumis pour savoir qui l'a dit."""

    segment_id: str
    text: str


def paroles(segments: list[TranscriptSegment]) -> list[Parole]:
    """Les passages dans l'ordre : c'est l'enchaînement qui fait reconnaître les rôles.

    Sert quand la transcription n'a séparé aucune voix — le cas de toutes les vraies
    consultations enregistrées jusqu'ici (26/09/2026).
    """
    return [
        Parole(segment_id=s.segment_id, text=s.text[:LONGUEUR_EXTRAIT])
        for s in sorted(segments, key=lambda s: s.start_ms)
        if s.text.strip()
    ]


def voix(segments: list[TranscriptSegment], speaker_labels: dict[str, str]) -> list[Voix]:
    """Les voix de la consultation, de la plus bavarde à la moins bavarde.

    Le temps de parole n'attribue aucun rôle à lui seul : il dit seulement laquelle
    des voix mérite qu'on regarde ses mots en premier.
    """
    groupes: dict[str, list[TranscriptSegment]] = defaultdict(list)
    for segment in segments:
        label = speaker_labels.get(segment.segment_id)
        if label is not None:
            groupes[label].append(segment)
    total = sum(max(0, s.end_ms - s.start_ms) for group in groupes.values() for s in group) or 1
    resume = []
    for label, group in groupes.items():
        duree = sum(max(0, s.end_ms - s.start_ms) for s in group)
        ordonnes = sorted(group, key=lambda s: s.start_ms)
        # Le début, puis des prises de parole réparties : une voix ne se reconnaît pas
        # qu'aux politesses d'ouverture.
        pas = max(1, len(ordonnes) // MAX_EXTRAITS)
        extraits = [s.text[:LONGUEUR_EXTRAIT] for s in ordonnes[::pas][:MAX_EXTRAITS]]
        resume.append(
            Voix(
                label=label,
                segments=len(group),
                duree_ms=duree,
                part=duree / total,
                premier_ms=ordonnes[0].start_ms,
                extraits=[e for e in extraits if e.strip()],
                indices=count_cues([s.text for s in group]),
            )
        )
    return sorted(resume, key=lambda v: (-v.duree_ms, v.premier_ms))


def appliquer(
    segments: list[TranscriptSegment], speaker_labels: dict[str, str], roles: dict[str, str]
) -> list[TranscriptSegment]:
    """Pose les rôles décidés voix par voix. Une voix sans rôle reste `unknown`."""
    return [
        segment.model_copy(
            update={
                "speaker_role": roles.get(speaker_labels.get(segment.segment_id, ""), "unknown")
            }
        )
        for segment in segments
    ]


def sans_role(segments: list[TranscriptSegment]) -> bool:
    """Reste-t-il une parole dont on ignore qui l'a dite ?"""
    return any(segment.speaker_role == "unknown" for segment in segments)
