"""Le plan de traitement mis en forme, sur la dictée de référence du Dr Moyal."""

from __future__ import annotations

from oris_api.documents.plan import plan_vue
from oris_api.documents.renderer import render_treatment_plan
from tests.test_redaction_consultation import dictee


def test_steps_follow_the_spoken_order_with_short_titles() -> None:
    vue = plan_vue(dictee())
    assert vue.numerote
    assert [e.titre for e in vue.etapes] == [
        "Greffe de conjonctif enfoui avec prélèvement tubérositaire bilatéral",
        "Port d'une gouttière conformatrice pendant 8 semaines après la greffe",
        "Réalisation de 2 bridges cantilever en zircone stratifiée",
        "Séance de préparation des bridges puis séance de collage 2 semaines après",
    ]
    # La parenthèse trop longue pour un titre devient une précision, pas un oubli.
    assert "12 avec ailette sur 11, 22 avec ailette sur 21." in vue.etapes[2].details


def test_delays_are_quoted_never_computed() -> None:
    assert [e.delai for e in plan_vue(dictee()).etapes] == [None, "8 semaines", None, "2 semaines"]


def test_the_refused_option_is_set_apart() -> None:
    vue = plan_vue(dictee())
    assert [e.titre for e in vue.ecartes] == ["Pose d'implants"]
    assert all("implant" not in e.titre.lower() for e in vue.etapes)


def test_missing_teeth_are_drawn_from_the_facts() -> None:
    assert set(plan_vue(dictee()).dents_absentes) == {"12", "22", "18", "28"}


def test_the_text_version_titles_each_step_and_keeps_the_chronology() -> None:
    contenu = render_treatment_plan(dictee()).content
    assert "Étape 1 — Greffe de conjonctif enfoui" in contenu
    assert "Chronologie" in contenu and "(8 semaines)" in contenu
    assert "Écarté" in contenu and "Pose d'implants (12, 22) — refusé." in contenu
