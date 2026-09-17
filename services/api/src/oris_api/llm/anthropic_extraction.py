"""Extraction clinique par Claude (API Messages d'Anthropic).

La sortie est imposée par un outil dont le schéma vient des contrats d'Oris. Une sortie
non conforme donne droit à un seul nouvel essai, avec l'erreur en retour, puis elle est
rejetée : jamais corrigée en silence (ACCEPTANCE_CRITERIA, extraction).
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from oris_api.contracts import (
    ClinicalFact,
    Procedure,
    TranscriptSegment,
    TreatmentPlan,
    validate_contract,
)
from oris_api.contracts.validation import ContractViolation
from oris_api.domain.resolver import resolve
from oris_api.domain.types import ExtractionResult, GlossaryHint
from oris_api.llm.prompt import (
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    TOOL_DESCRIPTION,
    TOOL_NAME,
    user_message,
)
from oris_api.llm.schema_bundle import extraction_tool_schema
from oris_api.providers.base import ExtractionUnavailable, ProviderInfo

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"
DEFAULT_MODEL = "claude-sonnet-5"
MAX_TOKENS = 8_000


class AnthropicExtractionProvider:
    """`ClinicalExtractionProvider` : segments → faits, plan et actes structurés."""

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        client: httpx.AsyncClient | None = None,
        timeout_s: float = 120,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._client = client
        self._timeout = timeout_s
        self.info = ProviderInfo(
            name="anthropic",
            version=f"{model}/{PROMPT_VERSION}",
            capabilities=["structured_output", "french"],
        )

    async def extract(
        self, segments: list[TranscriptSegment], glossary: list[GlossaryHint]
    ) -> ExtractionResult:
        if not segments:
            return ExtractionResult(facts=[])
        messages: list[dict[str, Any]] = [
            {"role": "user", "content": user_message(segments, glossary)}
        ]
        usage_total = {"input_tokens": 0, "output_tokens": 0}
        last_error: ContractViolation | ValueError | None = None

        # Un seul nouvel essai : le modèle reçoit l'emplacement exact de l'erreur.
        for attempt in range(2):
            raw, usage = await self._call(messages)
            usage_total = {k: usage_total[k] + usage.get(k, 0) for k in usage_total}
            try:
                result = self._build(raw, segments, usage_total)
                # Les règles déterministes d'Oris font partie du contrat : une sortie
                # qu'elles refusent donne droit au même unique nouvel essai, expliqué.
                violations = resolve(
                    result.facts,
                    result.treatment_plan,
                    result.procedures,
                    segments,
                    from_extraction=True,
                )
                if violations:
                    raise ValueError(
                        "règles cliniques non respectées : "
                        + ", ".join(f"{v.rule} ({v.subject_id})" for v in violations)
                    )
                return result
            except (ContractViolation, ValueError) as error:
                last_error = error
                if attempt == 1:
                    break
                messages += [
                    {
                        "role": "assistant",
                        "content": [{"type": "text", "text": json.dumps(raw, ensure_ascii=False)}],
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Sortie refusée : {error}.\n"
                            "Corrige uniquement ce point et renvoie la sortie complète. "
                            "N'ajoute aucune information absente des segments ; si un élément "
                            "ne peut pas être justifié, retire-le plutôt que de l'inventer."
                        ),
                    },
                ]
        raise ExtractionUnavailable("EXTRACTION_INVALID_OUTPUT") from last_error

    async def _call(self, messages: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, int]]:
        body = {
            "model": self._model,
            "max_tokens": MAX_TOKENS,
            "system": SYSTEM_PROMPT,
            "messages": messages,
            "tools": [
                {
                    "name": TOOL_NAME,
                    "description": TOOL_DESCRIPTION,
                    "input_schema": extraction_tool_schema(),
                }
            ],
            "tool_choice": {"type": "tool", "name": TOOL_NAME},
        }
        client = self._client or httpx.AsyncClient(timeout=self._timeout)
        try:
            response = await client.post(
                API_URL,
                headers={
                    "x-api-key": self._api_key,
                    "anthropic-version": API_VERSION,
                    "content-type": "application/json",
                },
                json=body,
            )
        except httpx.HTTPError as error:
            raise ExtractionUnavailable("ANTHROPIC_NETWORK") from error
        finally:
            if self._client is None:
                await client.aclose()

        if response.status_code in {401, 403}:
            raise ExtractionUnavailable("ANTHROPIC_AUTH")
        if response.status_code == 429 or response.status_code >= 500:
            raise ExtractionUnavailable(f"ANTHROPIC_HTTP_{response.status_code}")
        if response.status_code >= 400:
            raise ExtractionUnavailable(f"ANTHROPIC_REJECTED_{response.status_code}")

        payload = response.json()
        usage = payload.get("usage") or {}
        for block in payload.get("content") or []:
            if block.get("type") == "tool_use" and block.get("name") == TOOL_NAME:
                return dict(block.get("input") or {}), {
                    "input_tokens": int(usage.get("input_tokens", 0)),
                    "output_tokens": int(usage.get("output_tokens", 0)),
                }
        raise ExtractionUnavailable("ANTHROPIC_NO_TOOL_OUTPUT")

    def _build(
        self, raw: dict[str, Any], segments: list[TranscriptSegment], usage: dict[str, int]
    ) -> ExtractionResult:
        """Ajoute la provenance, valide chaque objet contre son contrat."""
        known = {segment.segment_id for segment in segments}
        facts = []
        for item in raw.get("facts") or []:
            if not isinstance(item, dict):
                raise ValueError("fait mal formé")
            fact = {**item, "source_type": "audio", "manually_validated": False}
            validate_contract("ClinicalFact", fact)
            if not set(fact["evidence_segment_ids"]) <= known:
                raise ValueError(f"preuve inconnue pour {fact['fact_id']}")
            facts.append(ClinicalFact.model_validate(fact))

        plan_payload = raw.get("treatment_plan")
        plan = None
        if plan_payload is not None:
            validate_contract("TreatmentPlan", plan_payload)
            plan = TreatmentPlan.model_validate(plan_payload)

        procedures = []
        for item in raw.get("procedures") or []:
            validate_contract("Procedure", item)
            procedures.append(Procedure.model_validate(item))

        return ExtractionResult(
            facts=facts,
            treatment_plan=plan,
            procedures=procedures,
            usage=usage,
            model=self._model,
        )
