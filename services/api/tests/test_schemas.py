"""Les contrats et les fixtures synthétiques sont valides et intègres."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

from oris_api.contracts.validation import SCHEMA_FILES, load_schema, validate_contract
from tests.conftest import REPO_ROOT

CORPUS_SCHEMA_PATH = REPO_ROOT / "corpus" / "synthetic_case.schema.json"


@pytest.mark.parametrize("filename", sorted(SCHEMA_FILES.values()))
def test_schema_is_valid_draft_2020_12(filename: str) -> None:
    Draft202012Validator.check_schema(load_schema(filename))


def test_every_schema_file_is_registered() -> None:
    on_disk = {p.name for p in (REPO_ROOT / "schemas").glob("*.schema.json")}
    assert on_disk == set(SCHEMA_FILES.values())


def corpus_validator() -> Draft202012Validator:
    """Le schéma du corpus référence `../schemas/…` relativement à son propre fichier."""

    def retrieve(uri: str) -> Resource[Any]:
        path = Path(uri.removeprefix("file://"))
        return DRAFT202012.create_resource(json.loads(path.read_text()))

    schema = json.loads(CORPUS_SCHEMA_PATH.read_text())
    schema["$id"] = CORPUS_SCHEMA_PATH.as_uri()
    return Draft202012Validator(schema, registry=Registry(retrieve=retrieve))  # type: ignore[call-arg]


def test_corpus_matches_manifest(corpus_cases: list[dict[str, Any]]) -> None:
    manifest = json.loads((REPO_ROOT / "corpus" / "manifest.json").read_text())
    raw = (REPO_ROOT / "corpus" / "synthetic_consultations_100.jsonl").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == manifest["sha256"]
    assert len(corpus_cases) == manifest["case_count"] == 100
    assert manifest["contains_real_patient_data"] is False
    domains: dict[str, int] = {}
    for case in corpus_cases:
        domains[case["domain"]] = domains.get(case["domain"], 0) + 1
    assert domains == manifest["domains"]


def test_every_corpus_case_matches_its_schema(corpus_cases: list[dict[str, Any]]) -> None:
    validator = corpus_validator()
    failures = {
        case["case_id"]: [e.json_path for e in validator.iter_errors(case)]
        for case in corpus_cases
        if not validator.is_valid(case)
    }
    assert failures == {}


def test_corpus_expected_objects_match_core_contracts(corpus_cases: list[dict[str, Any]]) -> None:
    for case in corpus_cases:
        for segment in case["transcript_segments"]:
            validate_contract("TranscriptSegment", segment)
        for fact in case["expected"]["facts"]:
            validate_contract("ClinicalFact", fact)
        if case["expected"]["treatment_plan"] is not None:
            validate_contract("TreatmentPlan", case["expected"]["treatment_plan"])
        for procedure in case["expected"]["procedures"]:
            validate_contract("Procedure", procedure)


def test_corpus_evidence_references_exist(corpus_cases: list[dict[str, Any]]) -> None:
    """Chaque preuve citée existe : segment pour un fait, fait pour un plan ou un acte."""
    for case in corpus_cases:
        segment_ids = {s["segment_id"] for s in case["transcript_segments"]}
        fact_ids = {f["fact_id"] for f in case["expected"]["facts"]}
        for fact in case["expected"]["facts"]:
            assert set(fact["evidence_segment_ids"]) <= segment_ids, case["case_id"]
        plan = case["expected"]["treatment_plan"]
        for item in plan["items"] if plan else []:
            assert set(item["evidence_fact_ids"]) <= fact_ids, case["case_id"]
        for procedure in case["expected"]["procedures"]:
            assert set(procedure["evidence_fact_ids"]) <= fact_ids, case["case_id"]


def test_critical_regression_cases_are_the_corpus_adversarial_cases(
    corpus_cases: list[dict[str, Any]], critical_cases: list[dict[str, Any]]
) -> None:
    adversarial = [case for case in corpus_cases if case["domain"] == "adversarial"]
    assert critical_cases == adversarial
    assert all("critical" in case["tags"] for case in critical_cases)


def test_contract_violation_never_quotes_values() -> None:
    fact = {"fact_id": "f1", "concept": "Dupont-secret", "teeth": ["19"]}
    with pytest.raises(ValueError) as caught:
        validate_contract("ClinicalFact", fact)
    assert "Dupont-secret" not in str(caught.value)
    assert "19" not in str(caught.value).replace("/teeth/0", "")
