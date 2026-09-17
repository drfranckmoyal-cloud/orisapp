"""Métriques du banc d'essai."""

from __future__ import annotations

from oris_api.benchmark import metrics


def test_tokenize_normalizes_case_punctuation_elisions_and_teeth() -> None:
    assert metrics.tokenize("Sur la 26… pardon, la vingt-sept : je n’ai PAS mal.") == [
        "sur",
        "la",
        "26",
        "pardon",
        "la",
        "27",
        "je",
        "n'",
        "ai",
        "pas",
        "mal",
    ]


def test_wer_counts_substitutions_deletions_insertions() -> None:
    ref = ["je", "n'", "ai", "pas", "de", "douleur"]
    hyp = ["je", "ai", "pas", "de", "grande", "douleur"]
    alignment = metrics.align(ref, hyp)
    assert alignment.errors == 2
    assert alignment.wer == 2 / 6


def test_identical_text_is_perfect() -> None:
    tokens = metrics.tokenize("Composite réalisé sur 11 aujourd'hui.")
    alignment = metrics.align(tokens, tokens)
    assert alignment.wer == 0
    assert metrics.tooth_accuracy(tokens, alignment).value == 1


def test_wrong_tooth_is_caught_even_if_wer_is_low() -> None:
    ref = metrics.tokenize("on retrouve l'ancienne restauration fracturée sur la 27 à reprendre")
    hyp = metrics.tokenize("on retrouve l'ancienne restauration fracturée sur la 26 à reprendre")
    alignment = metrics.align(ref, hyp)
    assert alignment.wer < 0.1
    assert metrics.tooth_accuracy(ref, alignment) == metrics.Ratio(0, 1)
    assert metrics.hallucinated_teeth(hyp, alignment) == 1


def test_lost_negation_is_caught() -> None:
    ref = metrics.tokenize("je n'ai pas de douleur nocturne")
    hyp = metrics.tokenize("j'ai de la douleur nocturne")
    alignment = metrics.align(ref, hyp)
    assert metrics.negation_preservation(ref, alignment) == metrics.Ratio(0, 2)


def test_term_recall_requires_the_whole_brand() -> None:
    ref = metrics.tokenize("adhésif Scotchbond Universal Plus puis Filtek Supreme XTE")
    hyp = metrics.tokenize("adhésif scotch bond universel plus puis Filtek Supreme XTE")
    recall = metrics.term_recall(
        ref, hyp, ["Scotchbond Universal Plus", "Filtek Supreme XTE", "Essentia"]
    )
    assert recall == metrics.Ratio(1, 2)


def test_speaker_accuracy_uses_best_label_mapping() -> None:
    reference = [
        metrics.TimedSpan(0, 1000, "patient"),
        metrics.TimedSpan(1000, 3000, "practitioner"),
    ]
    swapped = [metrics.TimedSpan(0, 1000, "B"), metrics.TimedSpan(1000, 3000, "A")]
    assert metrics.speaker_accuracy(reference, swapped) == 1.0
    merged = [metrics.TimedSpan(0, 3000, "A")]
    assert metrics.speaker_accuracy(reference, merged) == 2000 / 3000
    assert metrics.speaker_accuracy(reference, []) == 0.0


def test_percentiles() -> None:
    values = [float(v) for v in range(1, 101)]
    assert metrics.percentile(values, 50) == 50
    assert metrics.percentile(values, 95) == 95
    assert metrics.percentile([], 95) is None
