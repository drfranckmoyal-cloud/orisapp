"""Extraction clinique par Claude : requête, provenance, rejets et nouvel essai (sans réseau)."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx
import pytest

from oris_api.benchmark.extraction import score_case
from oris_api.contracts import TranscriptSegment
from oris_api.llm.anthropic_extraction import AnthropicExtractionProvider
from oris_api.llm.prompt import SYSTEM_PROMPT, TOOL_NAME
from oris_api.llm.schema_bundle import extraction_tool_schema
from oris_api.providers.base import ExtractionUnavailable
from oris_api.synthetic.corpus import default_corpus

SEGMENTS = [
    TranscriptSegment(
        segment_id="t1",
        start_ms=0,
        end_ms=2000,
        speaker_role="practitioner",
        text="Sur la 26… pardon, la 27, restauration fracturée.",
        confidence=0.9,
        is_final=True,
    ),
    TranscriptSegment(
        segment_id="t2",
        start_ms=2200,
        end_ms=4000,
        speaker_role="patient",
        text="Je n'ai pas mal.",
        confidence=0.9,
        is_final=True,
    ),
]


def fact(**overrides: Any) -> dict[str, Any]:
    base = {
        "fact_id": "f1",
        "category": "clinical_finding",
        "concept": "fractured_restoration",
        "value": "présente",
        "teeth": ["27"],
        "surfaces": [],
        "assertion": "present",
        "temporality": "current",
        "clinical_status": "observed",
        "speaker_role": "practitioner",
        "certainty": "certain",
        "evidence_segment_ids": ["t1"],
        "confidence": 0.9,
    }
    return {**base, **overrides}


def answer(payload: dict[str, Any], usage: tuple[int, int] = (100, 50)) -> dict[str, Any]:
    return {
        "content": [{"type": "tool_use", "name": TOOL_NAME, "input": payload}],
        "usage": {"input_tokens": usage[0], "output_tokens": usage[1]},
    }


def provider_with(responses: list[httpx.Response], seen: list[httpx.Request] | None = None) -> Any:
    queue = list(responses)

    def handler(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        return queue.pop(0)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return AnthropicExtractionProvider("sk-ant-test", "claude-sonnet-5", client=client)


def test_request_forces_the_oris_schema_and_prompt() -> None:
    seen: list[httpx.Request] = []
    provider = provider_with(
        [
            httpx.Response(
                200, json=answer({"facts": [fact()], "treatment_plan": None, "procedures": []})
            )
        ],
        seen,
    )
    asyncio.run(provider.extract(SEGMENTS, []))
    body = json.loads(seen[0].content)
    assert seen[0].headers["x-api-key"] == "sk-ant-test"
    assert seen[0].headers["anthropic-version"] == "2023-06-01"
    assert body["system"] == SYSTEM_PROMPT
    assert body["tool_choice"] == {"type": "tool", "name": TOOL_NAME}
    schema = body["tools"][0]["input_schema"]
    assert schema == extraction_tool_schema()
    # La provenance n'est pas laissée au modèle.
    assert "source_type" not in schema["properties"]["facts"]["items"]["properties"]
    assert "manually_validated" not in schema["properties"]["facts"]["items"]["properties"]
    sent = json.loads(body["messages"][0]["content"])
    assert [s["segment_id"] for s in sent["segments"]] == ["t1", "t2"]
    assert sent["concepts_connus"]["crack"] == "fissure"  # sens fourni, pas seulement le code


def test_provenance_is_set_by_oris_not_by_the_model() -> None:
    provider = provider_with(
        [
            httpx.Response(
                200, json=answer({"facts": [fact()], "treatment_plan": None, "procedures": []})
            )
        ]
    )
    result = asyncio.run(provider.extract(SEGMENTS, []))
    assert (result.facts[0].source_type, result.facts[0].manually_validated) == ("audio", False)
    assert result.usage == {"input_tokens": 100, "output_tokens": 50}
    assert result.model == "claude-sonnet-5"


def test_invented_evidence_is_refused_then_retried_once() -> None:
    seen: list[httpx.Request] = []
    provider = provider_with(
        [
            httpx.Response(
                200,
                json=answer(
                    {
                        "facts": [fact(evidence_segment_ids=["t9"])],
                        "treatment_plan": None,
                        "procedures": [],
                    }
                ),
            ),
            httpx.Response(
                200,
                json=answer(
                    {"facts": [fact()], "treatment_plan": None, "procedures": []}, usage=(120, 60)
                ),
            ),
        ],
        seen,
    )
    result = asyncio.run(provider.extract(SEGMENTS, []))
    assert len(seen) == 2, "un seul nouvel essai"
    retry = json.loads(seen[1].content)["messages"][-1]["content"]
    assert "preuve inconnue" in retry
    assert "sans rien inventer" in retry or "inventer" in retry
    # Les jetons des deux essais sont comptés.
    assert result.usage == {"input_tokens": 220, "output_tokens": 110}


def test_clinical_rule_violation_is_explained_then_retried() -> None:
    seen: list[httpx.Request] = []
    # Parole du patient promue en constat du praticien : interdit (test H).
    forbidden = fact(
        speaker_role="patient", clinical_status="observed", evidence_segment_ids=["t2"]
    )
    provider = provider_with(
        [
            httpx.Response(
                200, json=answer({"facts": [forbidden], "treatment_plan": None, "procedures": []})
            ),
            httpx.Response(
                200, json=answer({"facts": [fact()], "treatment_plan": None, "procedures": []})
            ),
        ],
        seen,
    )
    result = asyncio.run(provider.extract(SEGMENTS, []))
    assert "PATIENT_PROMOTED_TO_CLINICIAN" in json.loads(seen[1].content)["messages"][-1]["content"]
    assert result.facts[0].speaker_role == "practitioner"


def test_two_invalid_answers_are_rejected_never_coerced() -> None:
    bad = httpx.Response(
        200, json=answer({"facts": [fact(teeth=["19"])], "treatment_plan": None, "procedures": []})
    )
    provider = provider_with([bad, bad])
    with pytest.raises(ExtractionUnavailable) as caught:
        asyncio.run(provider.extract(SEGMENTS, []))
    assert caught.value.code == "EXTRACTION_INVALID_OUTPUT"


@pytest.mark.parametrize(
    ("status", "code"),
    [(401, "ANTHROPIC_AUTH"), (429, "ANTHROPIC_HTTP_429"), (529, "ANTHROPIC_HTTP_529")],
)
def test_provider_failures_are_explicit(status: int, code: str) -> None:
    provider = provider_with([httpx.Response(status, json={})])
    with pytest.raises(ExtractionUnavailable) as caught:
        asyncio.run(provider.extract(SEGMENTS, []))
    assert caught.value.code == code


def test_answer_without_tool_output_is_refused() -> None:
    provider = provider_with(
        [httpx.Response(200, json={"content": [{"type": "text", "text": "voici"}], "usage": {}})]
    )
    with pytest.raises(ExtractionUnavailable) as caught:
        asyncio.run(provider.extract(SEGMENTS, []))
    assert caught.value.code == "ANTHROPIC_NO_TOOL_OUTPUT"


def test_empty_transcript_costs_nothing() -> None:
    provider = provider_with([])
    assert asyncio.run(provider.extract([], [])).facts == []


def test_scoring_counts_matches_duplicates_and_axes() -> None:
    from oris_api.domain.types import ExtractionResult

    case = default_corpus().get("ORIS-SYN-092")
    assert case is not None
    # Sortie d'extraction : jamais « vérifiée par le praticien » (le corpus, lui, l'est).
    extracted = [f.model_copy(update={"manually_validated": False}) for f in case.facts]
    perfect = ExtractionResult(facts=extracted, usage={"input_tokens": 10, "output_tokens": 5})
    score = score_case(case, perfect, 1.0)
    assert (score.matched, score.expected, score.duplicates) == (2, 2, 0)
    assert score.negation_correct == score.negation_total == 2
    assert score.renderable == 2
    assert score.resolver_rules == ()

    wrong = [
        extracted[0].model_copy(update={"assertion": "present"}),
        extracted[1],
        extracted[1],
    ]
    degraded = score_case(case, ExtractionResult(facts=wrong), 1.0)
    assert degraded.duplicates == 1
    assert degraded.negation_correct < degraded.negation_total
