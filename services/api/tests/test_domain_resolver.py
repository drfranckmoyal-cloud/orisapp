"""Le résolveur rejette les sorties qui violent les invariants cliniques.

Chaque test part d'une extraction correcte du corpus, la dégrade comme le ferait
un modèle fautif, et vérifie le rejet. C'est ce qui protège la chaîne quand un
vrai extracteur remplacera le mock (M5).
"""

from __future__ import annotations

import pytest

from oris_api.contracts import ClinicalFact, TranscriptSegment, TreatmentPlan
from oris_api.domain.resolver import resolve
from oris_api.synthetic.corpus import SyntheticCase, default_corpus


def case(case_id: str) -> SyntheticCase:
    found = default_corpus().get(case_id)
    assert found is not None
    return found


def rules(
    facts: list[ClinicalFact],
    plan: TreatmentPlan | None,
    source: SyntheticCase,
    segments: list[TranscriptSegment] | None = None,
) -> set[str]:
    violations = resolve(facts, plan, list(source.procedures), segments or list(source.segments))
    return {v.rule for v in violations}


def with_fact(source: SyntheticCase, index: int, **changes: object) -> list[ClinicalFact]:
    facts = [f.model_copy(deep=True) for f in source.facts]
    facts[index] = facts[index].model_copy(update=changes)
    return facts


def test_all_corpus_cases_are_accepted() -> None:
    for source in default_corpus().cases():
        assert rules(list(source.facts), source.treatment_plan, source) == set(), source.case_id


def test_extraction_cannot_claim_practitioner_validation() -> None:
    source = case("ORIS-SYN-091")
    assert all(f.manually_validated for f in source.facts)  # vérité terrain du corpus
    violations = resolve(list(source.facts), source.treatment_plan, [], list(source.segments), True)
    assert {v.rule for v in violations} == {"EXTRACTION_SELF_VALIDATED"}


def test_g_future_act_marked_performed_is_rejected() -> None:
    source = case("ORIS-SYN-095")  # « la prochaine fois on fera les composites »
    facts = with_fact(source, 1, clinical_status="performed")
    assert "PERFORMED_IN_FUTURE" in rules(facts, None, source)


def test_h_patient_belief_promoted_to_diagnosis_is_rejected() -> None:
    source = case("ORIS-SYN-096")  # « je pense que c'est une carie »
    facts = with_fact(source, 0, clinical_status="clinician_assessment")
    assert "PATIENT_PROMOTED_TO_CLINICIAN" in rules(facts, None, source)
    facts = with_fact(source, 0, category="diagnosis")
    assert "PATIENT_PROMOTED_TO_CLINICIAN" in rules(facts, None, source)


def test_c_uncertainty_turned_certain_is_rejected() -> None:
    source = case("ORIS-SYN-093")  # « peut-être une fissure »
    facts = with_fact(source, 0, certainty="certain")
    assert "UNCERTAINTY_LOST" in rules(facts, source.treatment_plan, source)


@pytest.mark.parametrize("evidence", [[], ["s404"]])
def test_fact_without_real_evidence_is_rejected(evidence: list[str]) -> None:
    source = case("ORIS-SYN-091")
    facts = with_fact(source, 0, evidence_segment_ids=evidence)
    assert rules(facts, source.treatment_plan, source) & {"EVIDENCE_MISSING", "EVIDENCE_UNKNOWN"}


def test_j_fact_supported_only_by_audio_gap_is_rejected() -> None:
    source = case("ORIS-SYN-099")
    invented = ClinicalFact.model_validate(
        {**case("ORIS-SYN-091").facts[0].model_dump(), "evidence_segment_ids": ["s2"]}
    )
    assert "EVIDENCE_IS_AUDIO_GAP" in rules([invented], None, source)


def test_e_option_accepted_without_decision_is_rejected() -> None:
    source = case("ORIS-SYN-001")  # options discutées, aucune acceptée
    assert source.treatment_plan is not None
    plan = source.treatment_plan.model_copy(deep=True)
    plan.items[0].status = "accepted"
    assert "PLAN_STATUS_UNSUPPORTED" in rules(list(source.facts), plan, source)


def test_d_previous_proposal_cannot_become_plan() -> None:
    source = case("ORIS-SYN-094")  # facettes antérieures, composites retenus
    assert source.treatment_plan is not None
    plan = source.treatment_plan.model_copy(deep=True)
    plan.items[0].evidence_fact_ids = ["f1"]  # facettes, discutées dans le passé
    assert "PLAN_STATUS_UNSUPPORTED" in rules(list(source.facts), plan, source)


def test_a_plan_on_uncorrected_tooth_is_rejected() -> None:
    source = case("ORIS-SYN-091")  # « la 26… pardon, la 27 »
    assert source.treatment_plan is not None
    plan = source.treatment_plan.model_copy(deep=True)
    plan.items[0].teeth = ["26"]
    assert "PLAN_TEETH_UNSUPPORTED" in rules(list(source.facts), plan, source)


def test_usual_material_not_spoken_is_rejected() -> None:
    source = case("ORIS-SYN-051")  # composite avec matériaux réellement dits
    procedure = source.procedures[0].model_copy(deep=True)
    procedure.structured_data["etching"] = "acide orthophosphorique 37 %"
    violations = resolve(list(source.facts), None, [procedure], list(source.segments))
    assert "PROCEDURE_DATA_UNSUPPORTED" in {v.rule for v in violations}


def test_performed_procedure_without_performed_fact_is_rejected() -> None:
    source = case("ORIS-SYN-051")
    facts = [f.model_copy(update={"clinical_status": "planned"}) for f in source.facts]
    violations = resolve(facts, None, list(source.procedures), list(source.segments))
    assert "PROCEDURE_STATUS_UNSUPPORTED" in {v.rule for v in violations}
