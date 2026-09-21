"""Rédaction des documents et validateur factuel, sans base de données."""

from __future__ import annotations

from oris_api.contracts import ClinicalEncounter, EncounterWarning
from oris_api.documents.renderer import (
    NON_EXHAUSTIVE,
    render_consultation_note,
    render_treatment_plan,
)
from oris_api.domain.factual_validator import validate_document
from oris_api.domain.types import AudioGap, Claim, GeneratedDocument
from oris_api.domain.warnings import AUDIO_GAP_MESSAGE, compute_warnings
from oris_api.synthetic.corpus import default_corpus


def encounter(case_id: str, warnings: list[EncounterWarning] | None = None) -> ClinicalEncounter:
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
        warnings=warnings or [],
    )


def test_every_corpus_document_passes_the_factual_validator() -> None:
    for case in default_corpus().cases():
        obj = encounter(case.case_id)
        for document in (render_consultation_note(obj), render_treatment_plan(obj)):
            assert validate_document(document, obj) == [], (case.case_id, document.document_type)


def test_every_claim_cites_facts_and_every_fact_is_rendered() -> None:
    for case in default_corpus().cases():
        obj = encounter(case.case_id)
        note = render_consultation_note(obj)
        assert all(claim.fact_ids for claim in note.claims)
        assert set(note.supported_fact_ids) == {f.fact_id for f in obj.facts}


def test_empty_sections_are_omitted() -> None:
    note = render_consultation_note(encounter("ORIS-SYN-092"))
    assert note.content.splitlines()[0] == "Motif de la consultation"
    assert "Examen clinique" not in note.content


def test_sequence_number_only_when_explicit() -> None:
    """Sans rang dit, l'ordre de la dictée, sans numéro : un numéro inventé serait une
    chronologie inventée (décision du 21/09/2026)."""
    sans_rang = render_treatment_plan(encounter("ORIS-SYN-091")).content
    assert "Étape" not in sans_rang
    avec_rang = render_treatment_plan(encounter("ORIS-SYN-093")).content
    assert avec_rang.splitlines()[0].startswith("Étape 1 — ")


def test_audio_gap_is_critical_and_stated_in_document() -> None:
    warnings = compute_warnings([AudioGap(after_segment_id="s1", duration_ms=None)])
    assert [(w.code, w.severity, w.message) for w in warnings] == [
        ("AUDIO_GAP", "critical", AUDIO_GAP_MESSAGE)
    ]
    note = render_consultation_note(encounter("ORIS-SYN-099", warnings))
    assert NON_EXHAUSTIVE in note.content
    assert note.claims[0].warning_codes == ("AUDIO_GAP",)


def test_no_gap_no_warning() -> None:
    assert compute_warnings([]) == []


def test_validator_catches_tooth_not_in_facts() -> None:
    obj = encounter("ORIS-SYN-091")
    forged = GeneratedDocument(
        "consultation_note",
        "",
        (
            Claim("Examen clinique", "Constaté : restauration fracturée (26).", ("f1",)),
            Claim("Options", "Proposé : dépose (27).", ("f2",)),
        ),
    )
    codes = [issue.code for issue in validate_document(forged, obj)]
    assert codes == ["tooth_not_supported"]


def test_validator_catches_performed_claim_on_planned_fact() -> None:
    obj = encounter("ORIS-SYN-095")
    forged = GeneratedDocument(
        "consultation_note",
        "",
        (
            Claim("Actes", "Réalisé : composites additifs (11, 21).", ("f2",)),
            Claim("Actes", "Réalisé : photographies cliniques.", ("f1",)),
        ),
    )
    assert [i.code for i in validate_document(forged, obj)] == ["performed_not_supported"]


def test_validator_flags_unrendered_fact_for_review() -> None:
    obj = encounter("ORIS-SYN-092")
    partial = GeneratedDocument(
        "consultation_note",
        "",
        (Claim("S", "Rapporté par le patient : absence de x (16).", ("f1",)),),
    )
    issues = validate_document(partial, obj)
    assert [(i.code, i.severity, i.fact_id) for i in issues] == [
        ("fact_not_rendered", "review", "f2")
    ]


def test_unknown_concept_is_never_guessed() -> None:
    obj = encounter("ORIS-SYN-092")
    unknown = obj.facts[0].model_copy(update={"concept": "concept_inedit"})
    obj = obj.model_copy(update={"facts": [unknown]})
    note = render_consultation_note(obj)
    assert note.claims[0].text.startswith("À rédiger")
    assert [i.code for i in validate_document(note, obj)] == ["unrendered_concept"]
