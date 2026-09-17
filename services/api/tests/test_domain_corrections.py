"""Corrections structurées : application pure sur l'objet clinique."""

from __future__ import annotations

from itertools import pairwise

import pytest
from pydantic import TypeAdapter, ValidationError

from oris_api.contracts import ClinicalEncounter
from oris_api.domain.corrections import CorrectionError, CorrectionOperation, apply_operations
from oris_api.domain.lifecycle import TransitionError, ensure_transition
from oris_api.synthetic.corpus import default_corpus

OPERATIONS = TypeAdapter(list[CorrectionOperation])


def encounter(case_id: str) -> ClinicalEncounter:
    case = default_corpus().get(case_id)
    assert case is not None
    return ClinicalEncounter(
        encounter_id="enc",
        patient_id="pat",
        practitioner_id="usr",
        started_at="2026-09-17T09:00:00Z",
        ended_at=None,
        status="review",
        object_version=1,
        facts=list(case.facts),
        treatment_plan=case.treatment_plan,
        procedures=list(case.procedures),
        warnings=[],
    )


def ops(*raw: dict[str, object]) -> list[CorrectionOperation]:
    return OPERATIONS.validate_python(list(raw))


def test_replace_tooth_updates_facts_plan_and_bumps_version() -> None:
    before = encounter("ORIS-SYN-091")
    result = apply_operations(
        before, ops({"operation": "replace_tooth", "from_tooth": "27", "to_tooth": "26"})
    )
    after = result.encounter
    assert after.object_version == 2
    assert all(f.teeth == ["26"] for f in after.facts)
    assert after.treatment_plan is not None and after.treatment_plan.items[0].teeth == ["26"]
    assert all(f.manually_validated for f in after.facts)
    assert [e.event_type for e in result.learning_events] == ["tooth_number_correction"] * 2
    assert result.learning_events[0].before == {
        "fact_id": "f1",
        "concept": "fractured_restoration",
        "teeth": ["27"],
    }
    # L'objet d'origine n'est pas modifié.
    assert before.facts[0].teeth == ["27"]


def test_update_fact_emits_typed_learning_events() -> None:
    result = apply_operations(
        encounter("ORIS-SYN-093"),
        ops(
            {
                "operation": "update_fact",
                "fact_id": "f1",
                "changes": {"assertion": "present", "certainty": "certain"},
            }
        ),
    )
    types = sorted(e.event_type for e in result.learning_events)
    assert types == ["certainty_correction", "negation_correction"]


def test_plan_status_change_updates_clinical_object() -> None:
    result = apply_operations(
        encounter("ORIS-SYN-091"),
        ops({"operation": "set_plan_item_status", "item_id": "pi1", "status": "refused"}),
    )
    assert result.encounter.treatment_plan is not None
    assert result.encounter.treatment_plan.items[0].status == "refused"
    assert result.learning_events[0].event_type == "treatment_status_correction"


def test_added_fact_is_manual_with_no_invented_evidence() -> None:
    result = apply_operations(
        encounter("ORIS-SYN-092"),
        ops(
            {
                "operation": "add_fact",
                "fact": {
                    "category": "symptom",
                    "concept": "cold_sensitivity",
                    "value": "present",
                    "teeth": ["17"],
                    "assertion": "present",
                    "temporality": "current",
                    "clinical_status": "patient_reported",
                    "certainty": "certain",
                },
            }
        ),
    )
    added = result.encounter.facts[-1]
    assert (added.source_type, added.speaker_role, added.evidence_segment_ids) == (
        "manual",
        "manual",
        [],
    )
    assert result.learning_events[0].event_type == "clinical_fact_added"


def test_removing_a_fact_used_by_the_plan_is_refused() -> None:
    with pytest.raises(CorrectionError) as caught:
        apply_operations(
            encounter("ORIS-SYN-091"), ops({"operation": "remove_fact", "fact_id": "f2"})
        )
    assert caught.value.code == "FACT_REFERENCED"


@pytest.mark.parametrize(
    ("raw", "code"),
    [
        ({"operation": "replace_tooth", "from_tooth": "18", "to_tooth": "17"}, "TOOTH_NOT_FOUND"),
        (
            {"operation": "update_fact", "fact_id": "f9", "changes": {"certainty": "certain"}},
            "FACT_NOT_FOUND",
        ),
        ({"operation": "update_fact", "fact_id": "f1", "changes": {"teeth": ["27"]}}, "NO_CHANGE"),
    ],
)
def test_invalid_corrections_are_refused(raw: dict[str, object], code: str) -> None:
    with pytest.raises(CorrectionError) as caught:
        apply_operations(encounter("ORIS-SYN-091"), ops(raw))
    assert caught.value.code == code


def test_invalid_tooth_number_is_rejected_at_input() -> None:
    with pytest.raises(ValidationError):
        ops({"operation": "replace_tooth", "from_tooth": "27", "to_tooth": "19"})


def test_lifecycle_allows_documented_path_only() -> None:
    path = [
        "draft",
        "recording",
        "paused",
        "recording",
        "finalizing",
        "processing",
        "review",
        "validated",
        "exported",
        "archived",
    ]
    for current, target in pairwise(path):
        ensure_transition(current, target)  # type: ignore[arg-type]
    with pytest.raises(TransitionError):
        ensure_transition("draft", "validated")
    with pytest.raises(TransitionError):
        ensure_transition("processing", "validated")
    ensure_transition("generation_failed", "processing")
