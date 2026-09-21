"""Correction 26 → 27 de bout en bout, versions, invalidation, apprentissage, validation."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import pytest

from oris_api.domain.types import ExtractionResult
from oris_api.main import app
from oris_api.providers import ClinicalExtractionProvider, ProviderInfo, ProviderSet
from tests.conftest import clinical_object, documents_by_type, run_synthetic


class MisheardToothExtraction:
    """Extracteur qui a retenu 26 au lieu de 27 (erreur de modèle simulée)."""

    def __init__(self, inner: ClinicalExtractionProvider) -> None:
        self.info: ProviderInfo = inner.info
        self._inner = inner

    async def extract(self, segments: Any, glossary: Any) -> ExtractionResult:
        result: ExtractionResult = await self._inner.extract(segments, glossary)
        facts = [f.model_copy(update={"teeth": ["26"]}) for f in result.facts]
        plan = result.treatment_plan.model_copy(deep=True) if result.treatment_plan else None
        for item in plan.items if plan else []:
            item.teeth = ["26"]
        return ExtractionResult(facts, plan, result.procedures)


@pytest.fixture
def misheard(api: Any) -> Any:
    original: ProviderSet = app.state.providers
    app.state.providers = replace(
        original, clinical_extraction=MisheardToothExtraction(original.clinical_extraction)
    )
    yield api
    app.state.providers = original


def replace_tooth(api: Any, eid: str, version: int, regenerate: bool = True) -> Any:
    return api.patch(
        f"/encounters/{eid}/clinical-object",
        json={
            "expected_object_version": version,
            "regenerate": regenerate,
            "operations": [{"operation": "replace_tooth", "from_tooth": "26", "to_tooth": "27"}],
        },
    )


def test_tooth_correction_updates_object_then_regenerates_documents(misheard: Any) -> None:
    api = misheard
    eid = run_synthetic(api, "ORIS-SYN-091")["id"]
    before = documents_by_type(api, eid)
    assert "(26)" in before["consultation_note"]["content"]

    # 1. objet corrigé, documents invalidés (sans régénération pour observer l'état)
    corrected = replace_tooth(api, eid, 1, regenerate=False)
    assert corrected.status_code == 200, corrected.text
    assert corrected.json()["object_version"] == 2
    obj = clinical_object(api, eid)
    assert all(f["teeth"] == ["27"] for f in obj["facts"])
    assert obj["treatment_plan"]["items"][0]["teeth"] == ["27"]
    stale = documents_by_type(api, eid)
    assert {d["status"] for d in stale.values()} == {"outdated"}
    assert not stale["consultation_note"]["is_current"]
    validate = api.post(f"/documents/{stale['consultation_note']['id']}/validate", json={})
    assert validate.json()["code"] == "DOCUMENT_OUTDATED"

    # 2. régénération depuis l'objet v2
    regenerated = api.post(f"/encounters/{eid}/documents/generate").json()
    note = next(d for d in regenerated if d["document_type"] == "consultation_note")
    assert note["version"] == 2 and note["generated_from_object_version"] == 2
    assert "(27)" in note["content"] and "26" not in note["content"]
    assert note["status"] == "draft_ai"

    # 3. historique conservé
    versions = api.get(f"/encounters/{eid}/clinical-object").json()["versions"]
    assert [(v["version"], v["change_kind"]) for v in versions] == [
        (1, "extraction"),
        (2, "correction"),
    ]

    # 4. apprentissage
    events = api.get(f"/encounters/{eid}/learning-events").json()
    tooth_events = [e for e in events if e["event_type"] == "tooth_number_correction"]
    assert len(tooth_events) == 2
    assert tooth_events[0]["before"]["teeth"] == ["26"] and tooth_events[0]["after"]["teeth"] == [
        "27"
    ]
    assert tooth_events[0]["source_version"] == "clinical_object_v1"
    assert tooth_events[0]["validated_by_practitioner"] is True
    assert tooth_events[0]["eligible_for_global_learning"] is False


def test_correction_regenerates_by_default(misheard: Any) -> None:
    eid = run_synthetic(misheard, "ORIS-SYN-091")["id"]
    assert replace_tooth(misheard, eid, 1).status_code == 200
    docs = documents_by_type(misheard, eid)
    assert all(d["is_current"] and d["status"] == "draft_ai" for d in docs.values())
    assert "26" not in docs["treatment_plan_text"]["content"]


def test_stale_correction_is_refused(misheard: Any) -> None:
    eid = run_synthetic(misheard, "ORIS-SYN-091")["id"]
    assert replace_tooth(misheard, eid, 1).status_code == 200
    conflict = replace_tooth(misheard, eid, 1)
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "OBJECT_VERSION_CONFLICT"


def test_correction_breaking_invariants_is_rejected(api: Any) -> None:
    eid = run_synthetic(api, "ORIS-SYN-095")["id"]
    response = api.patch(
        f"/encounters/{eid}/clinical-object",
        json={
            "expected_object_version": 1,
            "operations": [
                {
                    "operation": "update_fact",
                    "fact_id": "f2",
                    "changes": {"clinical_status": "performed"},
                }
            ],
        },
    )
    assert response.status_code == 422
    assert response.json()["code"] == "CORRECTION_REJECTED"
    assert "PERFORMED_IN_FUTURE" in response.json()["details"]
    assert clinical_object(api, eid)["object_version"] == 1
    assert api.get(f"/encounters/{eid}/learning-events").json() == []


def test_explicit_validation_then_correction_reopens_review(api: Any) -> None:
    eid = run_synthetic(api, "ORIS-SYN-091")["id"]
    assert api.post(f"/encounters/{eid}/validate").json()["code"] == "DOCUMENTS_NOT_VALIDATED"
    for doc in documents_by_type(api, eid).values():
        validated = api.post(f"/documents/{doc['id']}/validate", json={})
        assert validated.status_code == 200 and validated.json()["status"] == "validated"
        assert api.post(f"/documents/{doc['id']}/validate", json={}).status_code == 409
    assert api.post(f"/encounters/{eid}/validate").json()["status"] == "validated"
    kinds = [e["event_type"] for e in api.get(f"/encounters/{eid}/learning-events").json()]
    assert kinds.count("document_validated_unchanged") == 2

    # Le patient a finalement accepté : décision explicite du praticien (spec §34).
    reopened = api.patch(
        f"/encounters/{eid}/clinical-object",
        json={
            "expected_object_version": 1,
            "operations": [
                {"operation": "set_plan_item_status", "item_id": "pi1", "status": "accepted"}
            ],
        },
    )
    assert reopened.status_code == 200, reopened.text
    assert reopened.json()["status"] == "review"
    docs = documents_by_type(api, eid)
    assert {d["status"] for d in docs.values()} == {"draft_ai"}
    note = docs["consultation_note"]["content"]
    assert "Accepté : dépose de la restauration et réévaluation (27)." in note
    assert "Statut : accepté." in docs["treatment_plan_text"]["content"]


def plan_de(api: Any, eid: str) -> list[dict[str, Any]]:
    objet = api.get(f"/encounters/{eid}/clinical-object").json()["clinical_object"]
    return list(objet["treatment_plan"]["items"]) if objet["treatment_plan"] else []


def corriger(api: Any, eid: str, version: int, operation: dict[str, Any]) -> Any:
    return api.patch(
        f"/encounters/{eid}/clinical-object",
        json={
            "expected_object_version": version,
            "operations": [operation],
            "regenerate": True,
        },
    )


def test_the_practitioner_adds_a_plan_item_of_his_own(api: Any) -> None:
    eid = run_synthetic(api, "ORIS-SYN-001")["id"]
    avant = len(plan_de(api, eid))
    reponse = corriger(
        api,
        eid,
        1,
        {"operation": "add_plan_item", "action": "gouttière de protection", "teeth": ["11"]},
    )
    assert reponse.status_code == 200, reponse.text
    apres = plan_de(api, eid)
    assert len(apres) == avant + 1
    ajoute = next(item for item in apres if item["action"] == "gouttière de protection")
    assert ajoute["status"] == "proposed"
    # Invariant 10 : l'élément est appuyé par un fait — ici la décision du praticien,
    # enregistrée comme telle, d'origine manuelle.
    objet = api.get(f"/encounters/{eid}/clinical-object").json()["clinical_object"]
    appui = next(fact for fact in objet["facts"] if fact["fact_id"] in ajoute["evidence_fact_ids"])
    assert appui["source_type"] == "manual" and appui["manually_validated"] is True
    assert appui["value"] == "gouttière de protection"
    # Le document suit.
    assert (
        "gouttière de protection"
        in documents_by_type(api, eid)["treatment_plan_text"]["content"].lower()
    )


def test_the_practitioner_removes_a_plan_item(api: Any) -> None:
    eid = run_synthetic(api, "ORIS-SYN-001")["id"]
    premier = plan_de(api, eid)[0]
    assert (
        corriger(
            api, eid, 1, {"operation": "remove_plan_item", "item_id": premier["item_id"]}
        ).status_code
        == 200
    )
    assert all(item["item_id"] != premier["item_id"] for item in plan_de(api, eid))


def test_reordering_the_plan_writes_an_explicit_sequence(api: Any) -> None:
    eid = run_synthetic(api, "ORIS-SYN-001")["id"]
    corriger(
        api,
        eid,
        1,
        {"operation": "add_plan_item", "action": "contrôle à trois mois"},
    )
    items = plan_de(api, eid)
    ordre = [item["item_id"] for item in items][::-1]
    assert (
        corriger(api, eid, 2, {"operation": "reorder_plan_items", "item_ids": ordre}).status_code
        == 200
    )

    apres = plan_de(api, eid)
    assert [item["item_id"] for item in apres] == ordre
    # §33.3 : l'ordre voulu par le praticien est une séquence énoncée.
    assert [item["sequence"] for item in apres] == list(range(1, len(apres) + 1))


def test_an_incomplete_order_is_refused(api: Any) -> None:
    eid = run_synthetic(api, "ORIS-SYN-001")["id"]
    corriger(api, eid, 1, {"operation": "add_plan_item", "action": "contrôle"})
    items = plan_de(api, eid)
    assert len(items) > 1
    refus = corriger(
        api, eid, 2, {"operation": "reorder_plan_items", "item_ids": [items[0]["item_id"]]}
    )
    assert refus.status_code == 422
    assert refus.json()["code"] == "PLAN_ORDER_INCOMPLETE"
