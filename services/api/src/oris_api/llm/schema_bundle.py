"""Schéma de sortie imposé au modèle, dérivé des JSON Schemas d'Oris.

Un seul vocabulaire : le modèle ne peut produire que ce que les contrats autorisent.
La provenance (`source_type`, `manually_validated`) est retirée du schéma : elle est
posée par Oris, jamais déclarée par le modèle.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from oris_api.contracts.validation import load_schema

PROVENANCE_FIELDS = ("source_type", "manually_validated")


def bare(name: str) -> dict[str, Any]:
    schema = deepcopy(load_schema(name))
    for key in ("$schema", "$id", "title"):
        schema.pop(key, None)
    return schema


def fact_schema() -> dict[str, Any]:
    schema = bare("clinical_fact.schema.json")
    for field in PROVENANCE_FIELDS:
        schema["properties"].pop(field, None)
    schema["required"] = [r for r in schema["required"] if r not in PROVENANCE_FIELDS]
    return schema


def extraction_tool_schema() -> dict[str, Any]:
    plan = bare("treatment_plan.schema.json")
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["facts", "treatment_plan", "procedures"],
        "properties": {
            "facts": {"type": "array", "items": fact_schema()},
            "treatment_plan": {"anyOf": [plan, {"type": "null"}]},
            "procedures": {"type": "array", "items": bare("procedure.schema.json")},
        },
    }
