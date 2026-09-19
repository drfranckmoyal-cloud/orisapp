"""Comptes rendus opératoires : modèles à emplacements, jamais de valeur par défaut."""

from __future__ import annotations

from typing import Any

from oris_api.contracts import ClinicalEncounter, Procedure
from oris_api.documents.operative_templates import TEMPLATES, template_for
from oris_api.documents.renderer import (
    missing_important_slots,
    procedure_claims,
    render_operative_note,
)
from oris_api.synthetic.corpus import default_corpus
from tests.conftest import documents_by_type, run_synthetic


def encounter_with(
    procedures: list[Procedure],
    case_id: str = "ORIS-SYN-041",
    facts: list[Any] | None = None,
) -> ClinicalEncounter:
    case = default_corpus().get(case_id)
    assert case is not None
    return ClinicalEncounter(
        encounter_id="e",
        patient_id="p",
        practitioner_id="u",
        started_at="2026-09-19T09:00:00Z",
        ended_at=None,
        status="review",
        object_version=1,
        facts=list(case.facts) if facts is None else facts,
        treatment_plan=case.treatment_plan,
        procedures=procedures,
        warnings=[],
    )


def procedure(**overrides: Any) -> Procedure:
    base = {
        "procedure_id": "pr1",
        "procedure_type": "composite",
        "status": "performed",
        "teeth": ["46"],
        "structured_data": {},
        "evidence_fact_ids": [],
    }
    return Procedure.model_validate({**base, **overrides})


def test_every_procedure_type_has_a_template() -> None:
    from typing import get_args

    from oris_api.contracts.generated import ProcedureProcedureType

    assert set(TEMPLATES) == set(get_args(ProcedureProcedureType))
    # Les emplacements d'un modèle sont uniques et rattachés à une section connue.
    for kind, slots in TEMPLATES.items():
        keys = [slot.key for slot in slots]
        assert len(keys) == len(set(keys)), kind


def test_an_empty_template_writes_nothing_but_the_act() -> None:
    """Aucune étape « normalement réalisée » n'apparaît d'elle-même (§37)."""
    claims = procedure_claims(procedure())
    assert [claim.text for claim in claims] == ["Restauration composite (46)."]


def test_the_usual_material_is_never_filled_in() -> None:
    """Rien n'a été dit sur le matériau : rien n'est écrit (critère M7)."""
    document = render_operative_note(encounter_with([procedure()], facts=[]))
    for habit in ("Filtek", "adhésif", "digue", "anesthésie"):
        assert habit.lower() not in document.content.lower()


def test_a_step_said_during_the_act_is_placed_in_its_slot_and_cites_its_fact() -> None:
    """Une étape dite et retenue comme fait appartient à l'acte : le document la place."""
    spoken = default_corpus().get("ORIS-SYN-041")
    assert spoken is not None
    claims = procedure_claims(procedure(), list(spoken.facts))
    written = {claim.text: claim.fact_ids for claim in claims}
    adhesive = next(text for text in written if text.startswith("Adhésif"))
    assert "G-Premio BOND" in adhesive
    # La phrase cite le fait qui porte l'information, pas l'acte en bloc.
    cited = written[adhesive][0]
    assert any(fact.fact_id == cited for fact in spoken.facts)


def test_only_spoken_slots_are_written() -> None:
    spoken = procedure(
        structured_data={"isolation": True, "adhesive": "G-Premio BOND", "sutures": "posées"}
    )
    text = "\n".join(claim.text for claim in procedure_claims(spoken))
    assert "Réalisé : isolation du champ opératoire." in text
    assert "Adhésif : G-Premio BOND." in text
    # « sutures » n'appartient pas au modèle composite : rien n'est inventé pour lui.
    assert "sutures" not in text.lower()


def test_an_explicit_no_is_written_as_a_no() -> None:
    text = "\n".join(
        claim.text for claim in procedure_claims(procedure(structured_data={"isolation": False}))
    )
    assert "Isolation du champ opératoire : non." in text


def test_a_missing_important_field_warns_and_is_not_filled() -> None:
    bare = procedure(structured_data={"isolation": True})
    missing = [slot.key for slot in missing_important_slots(bare)]
    assert missing == ["adhesive", "composite"]
    content = render_operative_note(encounter_with([bare], facts=[])).content
    assert "Adhésif" not in content and "Composite :" not in content


def test_a_planned_act_is_not_asked_for_its_materials(api: Any) -> None:
    """Un acte seulement prévu n'a ni matériau ni hémostase à documenter."""
    planned = procedure(status="planned")
    assert missing_important_slots(planned, []) == []


def test_a_cancelled_procedure_is_not_documented() -> None:
    document = render_operative_note(encounter_with([procedure(status="cancelled")], facts=[]))
    assert "Restauration composite" not in document.content


def test_sections_follow_the_template_order() -> None:
    full = procedure(
        structured_data={
            "complication": "aucune signalée",
            "adhesive": "G-Premio BOND",
            "isolation": True,
            "indication": "carie",
        }
    )
    sections = [claim.section for claim in procedure_claims(full, [])]
    assert sections == [
        "Acte réalisé",
        "Indication",
        "Isolation",
        "Matériaux utilisés",
        "Complications",
    ]


def test_extraction_template_covers_the_spec_fields() -> None:
    keys = {slot.key for slot in template_for("extraction")}
    assert {"anesthesia", "flap", "osteotomy", "tooth_sectioning", "hemostasis", "sutures"} <= keys
    important = {slot.key for slot in template_for("extraction") if slot.important}
    assert "postop_instructions" in important


def test_operative_note_is_not_produced_unless_asked(api: Any) -> None:
    eid = run_synthetic(api, "ORIS-SYN-041")["id"]
    assert "operative_note" not in documents_by_type(api, eid)

    created = api.post(f"/encounters/{eid}/documents/operative-note")
    assert created.status_code == 200
    note = documents_by_type(api, eid)["operative_note"]
    assert "Restauration composite (46)." in note["content"]
    assert note["status"] in {"draft_ai", "needs_review"}

    # Une fois demandé, il suit les corrections comme les autres documents.
    api.post(f"/encounters/{eid}/documents/generate")
    assert "operative_note" in documents_by_type(api, eid)


def test_a_consultation_without_procedure_refuses_the_operative_note(api: Any) -> None:
    eid = run_synthetic(api, "ORIS-SYN-092")["id"]
    refused = api.post(f"/encounters/{eid}/documents/operative-note")
    assert refused.status_code == 409
    assert refused.json()["code"] == "NO_PROCEDURE_TO_DOCUMENT"


def test_a_yes_no_slot_keeps_a_spoken_detail() -> None:
    """« provisoires réalisés le jour même » : la précision dite n'est pas jetée."""
    detailed = procedure(
        procedure_type="veneer_preparation",
        structured_data={"provisionals": "provisoires posés le jour même"},
    )
    text = "\n".join(claim.text for claim in procedure_claims(detailed, []))
    assert "Provisoires : provisoires posés le jour même." in text
