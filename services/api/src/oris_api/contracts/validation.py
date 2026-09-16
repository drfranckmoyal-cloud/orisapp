"""Validation normative contre les JSON Schemas de `schemas/`.

Les modèles Pydantic générés donnent des types ; ce module est l'arbitre du
contrat. Il couvre ce que Pydantic n'exprime pas (`uniqueItems`, références
entre fichiers) : une sortie de fournisseur IA ou un objet clinique passe ici
avant d'être accepté, et un échec est rejeté, jamais corrigé en silence.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from referencing import Registry
from referencing.jsonschema import DRAFT202012

SCHEMA_BASE_URI = "https://oris.local/schemas/"

SCHEMA_FILES = {
    "ClinicalEncounter": "clinical_encounter.schema.json",
    "ClinicalFact": "clinical_fact.schema.json",
    "Document": "document.schema.json",
    "EvaluationRun": "evaluation_run.schema.json",
    "LearningEvent": "learning_event.schema.json",
    "PractitionerLearningProfile": "practitioner_learning_profile.schema.json",
    "Procedure": "procedure.schema.json",
    "TranscriptSegment": "transcript_segment.schema.json",
    "TreatmentPlan": "treatment_plan.schema.json",
}


class ContractViolation(ValueError):
    """Un objet ne respecte pas son schéma. Le message ne cite aucune valeur."""

    def __init__(self, contract: str, paths: list[str]) -> None:
        self.contract = contract
        self.paths = paths
        super().__init__(f"{contract} invalide aux emplacements : {', '.join(paths)}")


def schema_dir() -> Path:
    override = os.environ.get("ORIS_SCHEMA_DIR")
    return Path(override) if override else Path(__file__).resolve().parents[5] / "schemas"


def load_schema(filename: str) -> dict[str, Any]:
    schema: dict[str, Any] = json.loads((schema_dir() / filename).read_text(encoding="utf-8"))
    return schema


@lru_cache
def registry() -> Registry[Any]:
    resources = []
    for filename in SCHEMA_FILES.values():
        resource = DRAFT202012.create_resource(load_schema(filename))
        resources.append((SCHEMA_BASE_URI + filename, resource))
    return Registry().with_resources(resources)


@lru_cache
def validator_for(contract: str) -> Draft202012Validator:
    schema = load_schema(SCHEMA_FILES[contract])
    return Draft202012Validator(schema, registry=registry())


def validate_contract(contract: str, instance: object) -> None:
    errors = sorted(validator_for(contract).iter_errors(instance), key=lambda e: list(e.path))
    if errors:
        paths = ["/" + "/".join(str(p) for p in error.absolute_path) for error in errors]
        raise ContractViolation(contract, paths)
