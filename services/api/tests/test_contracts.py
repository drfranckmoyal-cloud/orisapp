"""Les types générés sont à jour et fidèles aux schémas."""

from __future__ import annotations

import subprocess
import sys
from typing import Any

import pytest
from pydantic import ValidationError

from oris_api.contracts import ClinicalFact, TranscriptSegment, TreatmentPlan
from tests.conftest import REPO_ROOT


def test_generated_contracts_are_up_to_date() -> None:
    result = subprocess.run(  # noqa: S603
        [sys.executable, str(REPO_ROOT / "scripts" / "generate_contracts.py"), "--check"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout


def test_corpus_parses_into_generated_models(corpus_cases: list[dict[str, Any]]) -> None:
    for case in corpus_cases:
        for segment in case["transcript_segments"]:
            TranscriptSegment.model_validate(segment)
        for fact in case["expected"]["facts"]:
            parsed = ClinicalFact.model_validate(fact)
            assert parsed.model_dump(mode="json") == fact
        if case["expected"]["treatment_plan"] is not None:
            TreatmentPlan.model_validate(case["expected"]["treatment_plan"])


@pytest.mark.parametrize("tooth", ["19", "10", "56", "90", "1", "261"])
def test_invalid_fdi_tooth_numbers_are_rejected(
    tooth: str, corpus_cases: list[dict[str, Any]]
) -> None:
    fact = dict(corpus_cases[90]["expected"]["facts"][0], teeth=[tooth])
    with pytest.raises(ValidationError):
        ClinicalFact.model_validate(fact)


def test_unknown_fields_are_rejected(corpus_cases: list[dict[str, Any]]) -> None:
    fact = dict(corpus_cases[0]["expected"]["facts"][0], invented_field="x")
    with pytest.raises(ValidationError):
        ClinicalFact.model_validate(fact)
