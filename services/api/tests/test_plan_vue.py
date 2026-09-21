"""Le plan de traitement mis en forme, sur la dictée de référence du Dr Moyal."""

from __future__ import annotations

from oris_api.documents.plan import plan_vue
from oris_api.documents.renderer import render_treatment_plan
from tests.test_redaction_consultation import dictee


def test_steps_follow_the_spoken_order_with_short_titles() -> None:
    vue = plan_vue(dictee())
    assert vue.numerote
    assert [e.titre for e in vue.etapes] == [
        "Greffe de conjonctif enfoui",
        "Gouttière conformatrice",
        "2 bridges cantilever",
        "Préparation des bridges",
    ]
    # L'action complète, telle qu'elle a été dite, passe en première précision.
    assert vue.etapes[2].details[0].startswith("Réalisation de 2 bridges cantilever en zircone")


def test_titles_written_elsewhere_are_used_when_given() -> None:
    vue = plan_vue(dictee(), {"pi4": "Préparation puis collage"})
    assert vue.etapes[3].titre == "Préparation puis collage"


def test_delays_are_quoted_never_computed() -> None:
    assert [e.delai for e in plan_vue(dictee()).etapes] == [None, "8 semaines", None, "2 semaines"]


def test_the_refused_option_is_set_apart() -> None:
    vue = plan_vue(dictee())
    assert [e.titre for e in vue.ecartes] == ["Implants"]
    assert all("implant" not in e.titre.lower() for e in vue.etapes)


def test_missing_teeth_are_drawn_from_the_facts() -> None:
    assert set(plan_vue(dictee()).dents_absentes) == {"12", "22", "18", "28"}


def test_the_text_version_titles_each_step_and_keeps_the_chronology() -> None:
    contenu = render_treatment_plan(dictee()).content
    assert "Étape 1 — Greffe de conjonctif enfoui" in contenu
    assert "Étape 4 — Préparation des bridges" in contenu
    assert "Chronologie" in contenu and "(8 semaines)" in contenu
    assert "Écarté" in contenu and "Implants (12, 22) — refusé." in contenu


def test_stored_titles_are_read_back_from_the_document() -> None:
    from dataclasses import asdict

    from oris_api.documents.plan import titres_depuis

    document = render_treatment_plan(dictee(), {"pi4": "Préparation puis collage"})
    titres = titres_depuis([asdict(c) for c in document.claims])
    assert titres["pi4"] == "Préparation puis collage"
    assert titres["pi5"] == "Implants"
