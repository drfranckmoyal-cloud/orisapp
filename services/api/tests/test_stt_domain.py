"""Nombres dentaires dits en toutes lettres et rôles des locuteurs."""

from __future__ import annotations

import pytest

from oris_api.contracts import TranscriptSegment
from oris_api.domain.dental_numbers import normalize_tooth_numbers
from oris_api.domain.speaker_roles import apply_roles, assign_roles


@pytest.mark.parametrize(
    ("spoken", "expected"),
    [
        ("vingt six", ["26"]),
        ("vingt-six", ["26"]),
        ("onze", ["11"]),
        ("trente et un", ["31"]),
        ("quarante huit", ["48"]),
        ("quatre vingt cinq", ["85"]),
        ("dix neuf", ["dix", "neuf"]),  # 19 n'est pas un numéro FDI
        ("vingt", ["vingt"]),
        ("six mois", ["six", "mois"]),
    ],
)
def test_tooth_numbers_in_words(spoken: str, expected: list[str]) -> None:
    assert normalize_tooth_numbers(spoken.replace("-", " ").split()) == expected


def seg(segment_id: str, text: str) -> TranscriptSegment:
    return TranscriptSegment(
        segment_id=segment_id,
        start_ms=0,
        end_ms=1,
        speaker_role="unknown",
        text=text,
        confidence=0.9,
        is_final=True,
    )


def test_clinical_speaker_becomes_practitioner_other_patient() -> None:
    segments = [
        seg("t1", "Je voudrais quelque chose de naturel pour mon sourire, vraiment naturel."),
        seg(
            "t2",
            "Je note une usure et une fissure, je propose un composite après examen de la dent.",
        ),
        seg("t3", "D'accord, cela me convient tout à fait."),
    ]
    labels = {"t1": "1", "t2": "0", "t3": "1"}
    roles = [s.speaker_role for s in apply_roles(segments, labels)]
    assert roles == ["patient", "practitioner", "patient"]


def test_ambiguous_speakers_stay_unknown() -> None:
    segments = [
        seg("t1", "Bonjour comment allez vous aujourd'hui"),
        seg("t2", "Très bien merci et vous"),
    ]
    assignment = assign_roles(segments, {"t1": "0", "t2": "1"})
    assert not assignment.confident
    assert {s.speaker_role for s in apply_roles(segments, {"t1": "0", "t2": "1"})} == {"unknown"}


def test_single_dictating_practitioner_is_recognized() -> None:
    segments = [seg("t1", "Je note une fissure sur la 16, composite réalisé.")]
    assert apply_roles(segments, {"t1": "0"})[0].speaker_role == "practitioner"


def test_single_speaker_talking_like_a_patient_is_not_guessed() -> None:
    segments = [
        seg(
            "t1",
            "J'ai mal sur la 26 depuis que j'ai eu un composite, je pense que c'est une carie.",
        )
    ]
    assert apply_roles(segments, {"t1": "0"})[0].speaker_role == "unknown"


def test_patient_using_dental_words_is_never_taken_for_practitioner() -> None:
    """Phrases écrites hors corpus : le patient cite une dent et un matériau."""
    segments = [
        seg(
            "t1",
            "Docteur, j'ai mal sur la 26 depuis le composite, je crois que ça me fait mal au froid.",
        ),
        seg(
            "t2",
            "Je vous propose de refaire le test au froid. À l'examen, je ne vois pas de fissure sur la 26.",
        ),
        seg("t3", "D'accord, merci."),
    ]
    roles = [s.speaker_role for s in apply_roles(segments, {"t1": "A", "t2": "B", "t3": "A"})]
    assert roles == ["patient", "practitioner", "patient"]


def test_two_clinical_voices_are_left_unknown() -> None:
    segments = [
        seg("t1", "Je note une usure sur la 11, je propose un composite."),
        seg("t2", "On va préparer la digue, anesthésie locale réalisée sur la 11."),
    ]
    assert {s.speaker_role for s in apply_roles(segments, {"t1": "A", "t2": "B"})} == {"unknown"}
