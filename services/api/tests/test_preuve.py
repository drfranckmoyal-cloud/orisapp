"""« D'où vient cette phrase ? » : la preuve rendue au praticien (spec §30).

Le site le montrait déjà ; l'iPhone le montre aussi depuis le 26/09/2026, et tous
deux lisent la même route. Ces tests gardent l'invariant : une phrase ne montre que
des paroles réellement prononcées, et ne prétend jamais en avoir quand elle n'en a pas.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from oris_api.contracts import ClinicalEncounter, TranscriptSegment
from oris_api.services import preuve
from tests.conftest import documents_by_type, run_synthetic


def _segment(segment_id: str, start_ms: int, text: str, role: str = "patient") -> TranscriptSegment:
    return TranscriptSegment(
        segment_id=segment_id,
        start_ms=start_ms,
        end_ms=start_ms + 1_000,
        speaker_role=role,
        text=text,
        confidence=0.9,
        is_final=True,
    )


def _objet(facts: list[dict[str, Any]]) -> ClinicalEncounter:
    return ClinicalEncounter.model_validate(
        {
            "encounter_id": str(uuid4()),
            "patient_id": str(uuid4()),
            "practitioner_id": str(uuid4()),
            "started_at": "2026-09-26T09:00:00Z",
            "ended_at": None,
            "status": "review",
            "object_version": 1,
            "facts": facts,
            "treatment_plan": None,
            "procedures": [],
            "warnings": [],
        }
    )


def _fait(fact_id: str, segments: list[str], source_type: str = "audio") -> dict[str, Any]:
    return {
        "fact_id": fact_id,
        "category": "symptom",
        "concept": "cold_sensitivity",
        "value": None,
        "teeth": ["26"],
        "surfaces": [],
        "assertion": "present",
        "temporality": "past",
        "clinical_status": "patient_reported",
        "speaker_role": "patient",
        "certainty": "certain",
        "source_type": source_type,
        "evidence_segment_ids": segments,
        "confidence": 0.9,
        "manually_validated": False,
    }


def test_a_sentence_shows_its_words_once_and_in_the_order_they_were_spoken() -> None:
    rendu = preuve.construire(
        obj=_objet([_fait("f1", ["s2", "s1"]), _fait("f2", ["s1"])]),
        segments=[
            _segment("s1", 1_000, "ça me fait mal au froid"),
            _segment("s2", 5_000, "depuis trois semaines"),
        ],
        claims=[{"section": "Motif", "text": "Sensibilité au froid.", "fact_ids": ["f1", "f2"]}],
        document_id=uuid4(),
        version=1,
        object_version=1,
    )
    phrase = rendu.phrases[0]
    # Le segment s1, cité par deux faits, n'apparaît qu'une fois ; l'ordre est celui
    # de la consultation, pas celui des faits.
    assert [p.segment_id for p in phrase.passages] == ["s1", "s2"]
    assert phrase.sans_preuve is False
    assert phrase.saisi_a_la_main is False
    # Le concept est rendu dans les mots du praticien.
    assert phrase.faits[0].libelle == "sensibilité au froid"


def test_a_sentence_without_recoverable_words_says_so_instead_of_pretending() -> None:
    rendu = preuve.construire(
        obj=_objet([_fait("f1", [], source_type="manual")]),
        segments=[],
        claims=[
            {"section": "Motif", "text": "Fait saisi par le praticien.", "fact_ids": ["f1"]},
            {
                "section": "Motif",
                "text": "Phrase d'alerte.",
                "fact_ids": [],
                "warning_codes": ["X"],
            },
        ],
        document_id=uuid4(),
        version=1,
        object_version=1,
    )
    saisi, alerte = rendu.phrases
    assert saisi.sans_preuve is True and saisi.saisi_a_la_main is True
    assert alerte.sans_preuve is True and alerte.saisi_a_la_main is False
    assert rendu.transcription_disponible is False


def test_an_unknown_fact_id_is_ignored_rather_than_invented() -> None:
    rendu = preuve.construire(
        obj=_objet([]),
        segments=[_segment("s1", 0, "bonjour")],
        claims=[{"section": "Motif", "text": "Phrase.", "fact_ids": ["fantome"]}],
        document_id=uuid4(),
        version=1,
        object_version=1,
    )
    assert rendu.phrases[0].faits == []
    assert rendu.phrases[0].passages == []


def test_the_route_returns_the_words_behind_each_sentence_of_a_real_document(api: Any) -> None:
    encounter = run_synthetic(api, "ORIS-SYN-001")
    document = documents_by_type(api, encounter["id"])["consultation_note"]
    dit = {
        segment["segment_id"]: segment["text"]
        for segment in api.get(f"/encounters/{encounter['id']}/transcript").json()["segments"]
    }

    rendu = api.get(f"/documents/{document['id']}/preuve").json()
    assert rendu["document_id"] == document["id"]
    assert rendu["transcription_disponible"] is True
    assert [p["text"] for p in rendu["phrases"]] == [c["text"] for c in document["claims"]]

    appuyees = [p for p in rendu["phrases"] if p["faits"]]
    assert appuyees, "un document rédigé cite forcément des faits"
    for phrase in appuyees:
        # Aucune parole inventée : chaque passage est un segment de la consultation,
        # avec son texte exact.
        for passage in phrase["passages"]:
            assert dit[passage["segment_id"]] == passage["text"]


def test_the_preuve_of_an_unknown_document_is_a_404(api: Any) -> None:
    response = api.get(f"/documents/{uuid4()}/preuve")
    assert response.status_code == 404
    assert response.json()["code"] == "DOCUMENT_NOT_FOUND"
