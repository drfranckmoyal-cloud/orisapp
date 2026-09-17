"""Attribution des rôles aux locuteurs détectés par le STT (spec §15).

Principe : une erreur de rôle est dangereuse (une impression du patient deviendrait
un constat du praticien). La règle cherche donc des **tournures propres à chaque rôle**
(« je note », « je propose », « à l'examen » ; « j'ai mal », « je préfère », « je pense
que ») plutôt qu'un vocabulaire commun, et laisse `unknown` dès que ce n'est pas net.
Le praticien pourra corriger un rôle ; l'extraction ne se fie jamais à un rôle inconnu.
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


def apply_roles(
    segments: list[TranscriptSegment], speaker_labels: dict[str, str]
) -> list[TranscriptSegment]:
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
