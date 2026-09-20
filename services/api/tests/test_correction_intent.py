"""Interprétation des corrections dictées : patch structuré, jamais de devinette."""

from __future__ import annotations

from oris_api.contracts import ClinicalEncounter
from oris_api.domain.correction_intent import interpret
from oris_api.synthetic.corpus import default_corpus


def encounter(case_id: str = "ORIS-SYN-001") -> ClinicalEncounter:
    case = default_corpus().get(case_id)
    assert case is not None
    return ClinicalEncounter(
        encounter_id="e",
        patient_id="p",
        practitioner_id="u",
        started_at="2026-09-20T09:00:00Z",
        ended_at=None,
        status="review",
        object_version=1,
        facts=list(case.facts),
        treatment_plan=case.treatment_plan,
        procedures=list(case.procedures),
        warnings=[],
    )


def test_replacing_a_tooth_is_understood_in_several_phrasings() -> None:
    obj = encounter("ORIS-SYN-092")  # porte la dent 16
    for phrase in (
        "remplace 16 par 17",
        "Remplacez la 16 par la 17.",
        "pas la 16, la 17",
        "la 16 c'est la 17",
        "corrige la 16 en 17",
    ):
        result = interpret(phrase, obj)
        assert result.kind == "clinical", phrase
        assert result.operations[0].model_dump() == {
            "operation": "replace_tooth",
            "from_tooth": "16",
            "to_tooth": "17",
            "fact_ids": None,
        }
        # Changer une dent est toujours à confirmer.
        assert result.impact == "high"


def test_a_tooth_absent_from_the_record_is_refused_not_invented() -> None:
    result = interpret("remplace 35 par 36", encounter("ORIS-SYN-092"))
    assert result.kind == "unclear"
    assert "35" in result.reason


def test_an_acceptance_changes_the_plan_status() -> None:
    result = interpret("le patient a finalement accepté les composites", encounter())
    assert result.kind == "clinical"
    operation = result.operations[0].model_dump()
    assert operation["operation"] == "set_plan_item_status"
    assert operation["status"] == "accepted"
    assert result.impact == "high"


def test_an_ambiguous_target_asks_instead_of_choosing() -> None:
    result = interpret("retire la phrase", encounter())
    assert result.kind == "unclear"
    assert "Précisez" in result.reason


def test_removing_a_named_element_is_understood_and_flagged_high() -> None:
    obj = encounter("ORIS-SYN-092")
    result = interpret("retire la phrase sur la sensibilité au froid", obj)
    assert result.kind == "clinical"
    assert result.operations[0].model_dump()["operation"] == "remove_fact"
    assert result.impact == "high"


def test_adding_a_tooth_to_an_element() -> None:
    obj = encounter()
    result = interpret("l'asymétrie de forme concerne aussi la 12", obj)
    assert result.kind == "clinical"
    operation = result.operations[0].model_dump()
    assert operation["operation"] == "update_fact"
    assert "12" in operation["changes"]["teeth"]


def test_a_style_request_never_touches_the_record() -> None:
    for phrase in ("fais le compte rendu plus court", "reformule ça autrement"):
        result = interpret(phrase, encounter())
        assert result.kind == "editorial", phrase
        assert result.operations == []


def test_an_unknown_command_is_returned_with_examples() -> None:
    result = interpret("mets une couronne sur la 14", encounter())
    assert result.kind == "unclear"
    assert "remplace 26 par 27" in result.reason


def test_an_empty_command_says_so() -> None:
    assert interpret("   ", encounter()).kind == "unclear"
