"""Tests critiques A–J (spec §74) de bout en bout via l'API.

Avec l'extracteur mock, ces tests prouvent que la chaîne conserve jusqu'aux
documents la dent, la négation, l'incertitude, la temporalité et le statut
extraits, et que la validation reste explicite. Les rejets de sorties fautives
sont couverts par tests/test_domain_resolver.py. La qualité d'extraction depuis
la parole réelle sera évaluée en M5.
"""

from __future__ import annotations

from typing import Any

from tests.conftest import clinical_object, documents_by_type, run_synthetic


def run(api: Any, case_id: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, dict[str, Any]]]:
    encounter = run_synthetic(api, case_id)
    assert encounter["status"] == "review", encounter["processing_errors"]
    return encounter, clinical_object(api, encounter["id"]), documents_by_type(api, encounter["id"])


def facts_by_concept(obj: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {fact["concept"]: fact for fact in obj["facts"]}


def test_a_tooth_correction_in_speech_keeps_final_tooth(api: Any) -> None:
    _, obj, docs = run(api, "ORIS-SYN-091")  # « Sur la 26… pardon, la 27 »
    assert {t for f in obj["facts"] for t in f["teeth"]} == {"27"}
    assert obj["treatment_plan"]["items"][0]["teeth"] == ["27"]
    for doc in docs.values():
        assert "26" not in doc["content"]
        assert "27" in doc["content"]


def test_b_negation_is_preserved(api: Any) -> None:
    _, obj, docs = run(api, "ORIS-SYN-092")  # « Je n'ai pas de douleur nocturne »
    pain = facts_by_concept(obj)["nocturnal_pain"]
    assert pain["assertion"] == "absent"
    note = docs["consultation_note"]["content"]
    assert "absence de douleur nocturne" in note
    assert "Rapporté par le patient : douleur nocturne" not in note


def test_c_uncertainty_is_preserved(api: Any) -> None:
    _, obj, docs = run(api, "ORIS-SYN-093")  # « peut-être une fissure sur 16 »
    crack = facts_by_concept(obj)["crack"]
    assert (crack["assertion"], crack["certainty"]) == ("uncertain", "possible")
    note = docs["consultation_note"]["content"]
    assert "Suspicion de fissure (16), non confirmée." in note
    assert "Présence d’une fissure" not in note and "Constaté : fissure" not in note


def test_d_previous_proposal_is_not_the_current_plan(api: Any) -> None:
    _, obj, docs = run(api, "ORIS-SYN-094")  # facettes proposées avant, composites aujourd'hui
    veneers = facts_by_concept(obj)["veneers"]
    assert (veneers["temporality"], veneers["clinical_status"]) == ("past", "discussed")
    items = obj["treatment_plan"]["items"]
    assert [i["action"] for i in items] == ["composites additifs"]
    assert "facette" not in docs["treatment_plan_text"]["content"]
    assert (
        "Option évoquée antérieurement : facettes (11, 21)." in docs["consultation_note"]["content"]
    )


def test_e_discussed_options_stay_undecided(api: Any) -> None:
    _, obj, docs = run(api, "ORIS-SYN-001")  # blanchiment ou ne rien faire, sans décision
    options = [f for f in obj["facts"] if f["category"] == "treatment_option"]
    assert len(options) == 2 and {f["clinical_status"] for f in options} == {"discussed"}
    assert all(f["clinical_status"] != "accepted" for f in obj["facts"])
    assert all(i["status"] != "accepted" for i in obj["treatment_plan"]["items"])
    assert "Accepté" not in docs["consultation_note"]["content"]
    assert "accepté" not in docs["treatment_plan_text"]["content"]


def test_f_performed_today_is_performed_without_invented_details(api: Any) -> None:
    _, obj, docs = run(api, "ORIS-SYN-100")  # « Composite réalisé sur 11 aujourd'hui »
    composite = facts_by_concept(obj)["composite_restoration"]
    assert (composite["clinical_status"], composite["teeth"]) == ("performed", ["11"])
    note = docs["consultation_note"]["content"]
    assert "Réalisé : restauration composite (11)." in note
    # Spec §20 : ni digue, ni mordançage, ni adhésif, ni teinte non prononcés.
    for invented in ("digue", "mordan", "adhésif", "A2", "Matériau"):
        assert invented not in note
    assert obj["procedures"] == []


def test_g_next_visit_is_planned_not_performed(api: Any) -> None:
    _, obj, docs = run(api, "ORIS-SYN-095")  # « la prochaine fois on fera les composites »
    composites = facts_by_concept(obj)["additive_composites"]
    assert (composites["clinical_status"], composites["temporality"]) == ("planned", "future")
    note = docs["consultation_note"]["content"]
    assert "Prévu : composites additifs (11, 21)." in note
    assert "Réalisé : composites" not in note
    assert obj["treatment_plan"]["items"][0]["status"] == "planned"


def test_h_patient_belief_is_not_a_diagnosis(api: Any) -> None:
    _, obj, docs = run(api, "ORIS-SYN-096")  # « je pense que c'est une carie »
    belief = facts_by_concept(obj)["patient_belief_caries"]
    assert (belief["speaker_role"], belief["clinical_status"]) == ("patient", "patient_reported")
    assessment = facts_by_concept(obj)["caries_diagnosis"]
    assert assessment["assertion"] == "absent"
    note = docs["consultation_note"]["content"]
    assert "Impression du patient, non confirmée : carie." in note
    assert "Non retenu à ce stade : carie." in note
    assert "Évaluation : carie" not in note and "Constaté : carie" not in note


def test_i_stopped_medication_is_not_current(api: Any) -> None:
    _, obj, docs = run(api, "ORIS-SYN-097")  # « je ne le prends plus depuis six mois »
    current = next(f for f in obj["facts"] if f["category"] == "medication")
    assert (current["assertion"], current["temporality"]) == ("absent", "current")
    note = docs["consultation_note"]["content"]
    assert "Eliquis : n’est plus pris actuellement" in note
    assert "Traitement en cours" not in note


def test_j_audio_gap_blocks_false_completeness(api: Any) -> None:
    encounter, obj, docs = run(api, "ORIS-SYN-099")  # coupure audio
    assert obj["warnings"] == [
        {
            "code": "AUDIO_GAP",
            "severity": "critical",
            "message": "Une portion significative de la consultation n’a pas été captée.",
        }
    ]
    assert encounter["critical_warning_count"] == 1
    note = docs["consultation_note"]
    assert "ne peut pas être considéré comme exhaustif" in note["content"]
    # Validation impossible sans reconnaissance explicite de l'alerte.
    refused = api.post(f"/documents/{note['id']}/validate", json={})
    assert refused.status_code == 409
    assert refused.json() == {
        "code": "WARNING_NOT_ACKNOWLEDGED",
        "subject_id": note["id"],
        "details": ["AUDIO_GAP"],
    }
    accepted = api.post(
        f"/documents/{note['id']}/validate", json={"acknowledged_warning_codes": ["AUDIO_GAP"]}
    )
    assert accepted.status_code == 200
    events = api.get(f"/encounters/{encounter['id']}/learning-events").json()
    assert "warning_confirmed" in {e["event_type"] for e in events}


def test_speaker_conflict_keeps_both_statements(api: Any) -> None:
    _, _, docs = run(api, "ORIS-SYN-098")  # patient : 26 ; examen : 27, pas 26
    note = docs["consultation_note"]["content"]
    assert "Impression du patient, non confirmée : douleur localisée (26)." in note
    assert "Constaté : douleur reproduite (27)." in note
    assert "Non constaté : douleur reproduite (26)." in note


def test_no_document_is_validated_without_practitioner_action(api: Any) -> None:
    for case_id in ("ORIS-SYN-091", "ORIS-SYN-051", "ORIS-SYN-099"):
        encounter, _, docs = run(api, case_id)
        assert encounter["status"] == "review"
        assert all(
            doc["status"] != "validated" and doc["validated_at"] is None for doc in docs.values()
        )
