"""Rédaction du compte rendu de consultation avec les mots dits (modèle du Dr Moyal).

Cas réel de référence : une dictée du Dr Moyal du 21/09/2026, rubrique par rubrique,
sans patient réel. L'ancienne rédaction remplaçait les mots dits par des libellés de
liste et faisait dire au compte rendu le contraire de la dictée. Ces tests tiennent
que chacune de ces erreurs ne revient pas.
"""

from __future__ import annotations

import json
from pathlib import Path

from oris_api.contracts import ClinicalEncounter
from oris_api.documents.renderer import RUBRIQUES_CONSULTATION, render_consultation_note
from oris_api.domain.factual_validator import validate_document

FIXTURE = Path(__file__).parent / "fixtures" / "dictee_bridges_cantilever.json"


def dictee() -> ClinicalEncounter:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return ClinicalEncounter(
        encounter_id="enc",
        patient_id="pat",
        practitioner_id="usr",
        started_at="2026-09-21T09:00:00Z",
        ended_at=None,
        status="review",
        object_version=1,
        facts=data["facts"],
        treatment_plan=data["treatment_plan"],
        procedures=data["procedures"],
        warnings=[],
    )


def rubrique(contenu: str, titre: str) -> str:
    lignes = contenu.splitlines()
    debut = lignes.index(titre) + 1
    fin = next((i for i in range(debut, len(lignes)) if lignes[i] == ""), len(lignes))
    return "\n".join(lignes[debut:fin])


def test_the_dictated_words_are_kept() -> None:
    note = render_consultation_note(dictee()).content
    for dit in (
        "Agénésie de 12 et 22",
        "11, 13, 21, 23 sont en bon état",
        "Espace mésiodistal entre 11 et 13, et 21 et 23 est suffisant",
        "gouttière conformatrice",
        "2 bridges cantilever séparés",
        "ailette sur 11",
        "zircone stratifiée",
        "0,3 à 0,5 mm d'épaisseur en palatin",
        "Patient adressé par le docteur Martin",
    ):
        assert dit in note, dit


def test_none_of_the_old_misreadings_come_back() -> None:
    note = render_consultation_note(dictee()).content
    for faux in (
        "Non constaté : bridge en place",
        "disharmonie dento-dentaire",
        "préparation pour facettes",
        "Gouttière occlusale",
        "adressage à un confrère",
        "non reconnu par Oris",
        "Constaté :",
        "Rapporté par le patient :",
    ):
        assert faux not in note, faux


def test_the_rubrics_follow_the_template_order_and_empty_ones_vanish() -> None:
    note = render_consultation_note(dictee()).content
    titres = [ligne for ligne in note.splitlines() if ligne in RUBRIQUES_CONSULTATION]
    assert titres == [t for t in RUBRIQUES_CONSULTATION if t in titres]
    assert len(titres) == len(RUBRIQUES_CONSULTATION)


def test_a_proposal_said_twice_is_written_once() -> None:
    proposition = rubrique(render_consultation_note(dictee()).content, "Proposition thérapeutique")
    assert proposition.count("bridges cantilever séparés") == 1
    assert "Proposé : bridge" not in proposition


def test_ruled_out_and_refused_options_stay_out_of_the_proposal() -> None:
    contenu = render_consultation_note(dictee()).content
    assert "implant" not in rubrique(contenu, "Proposition thérapeutique").lower()
    attention = rubrique(contenu, "Points d’attention / coordination")
    assert "impossibilité de réaliser" in attention
    assert "refuse" in attention


def test_the_dictation_passes_the_factual_validator_and_renders_every_fact() -> None:
    encounter = dictee()
    note = render_consultation_note(encounter)
    assert validate_document(note, encounter) == []
    assert set(note.supported_fact_ids) == {fact.fact_id for fact in encounter.facts}


def test_a_denied_fact_whose_words_do_not_deny_is_flagged_for_review() -> None:
    encounter = dictee()
    fact = encounter.facts[2].model_copy(
        update={"assertion": "absent", "value": "Douleur spontanée sur la 36 depuis hier"}
    )
    encounter = encounter.model_copy(update={"facts": [fact]})
    note = render_consultation_note(encounter)
    codes = [issue.code for issue in validate_document(note, encounter)]
    assert "negation_unclear" in codes


def test_a_referral_letter_is_built_from_the_same_facts_in_the_letter_rubrics() -> None:
    from oris_api.documents.renderer import RUBRIQUES_COURRIER, render_referral_letter

    encounter = dictee()
    lettre = render_referral_letter(encounter)
    titres = [ligne for ligne in lettre.content.splitlines() if ligne in RUBRIQUES_COURRIER]
    assert titres == [t for t in RUBRIQUES_COURRIER if t in titres]
    assert "Agénésie de 12 et 22" in rubrique(lettre.content, "Contexte clinique")
    assert "Radiographie panoramique" in rubrique(
        lettre.content, "Examens disponibles / pièces jointes"
    )
    # Rien n'a été dit sur ce qu'on demande au confrère : la rubrique n'existe pas.
    assert "Demande / objectifs" not in titres
    assert validate_document(lettre, encounter) == []
