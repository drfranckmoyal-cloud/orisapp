"""Validateur factuel déterministe (spec §29, docs/AI_ARCHITECTURE.md §7).

Vérifie chaque phrase d'un document contre l'objet clinique. Ne peut ajouter
aucun fait ; il signale. Un problème critique bloque la validation du document.
"""

from __future__ import annotations

import re

from oris_api.contracts import ClinicalEncounter
from oris_api.documents.renderer import (
    UNRENDERED_PREFIX,
    missing_important_slots,
    negation_ecrite,
)
from oris_api.domain.types import GeneratedDocument, ValidationIssue

# Numéros FDI permanents et temporaires isolés dans le texte.
TOOTH_IN_TEXT = re.compile(r"(?<![\d,.])([1-4][1-8]|[5-8][1-5])(?![\d,.]\d)")


def validate_document(
    document: GeneratedDocument, encounter: ClinicalEncounter
) -> list[ValidationIssue]:
    facts = {fact.fact_id: fact for fact in encounter.facts}
    warning_codes = {warning.code for warning in encounter.warnings}
    issues: list[ValidationIssue] = []

    for index, claim in enumerate(document.claims):
        if not claim.fact_ids and not claim.warning_codes:
            issues.append(ValidationIssue("unsupported_claim", "critical", claim_index=index))
            continue
        if not set(claim.warning_codes) <= warning_codes:
            issues.append(ValidationIssue("unsupported_claim", "critical", claim_index=index))
        unknown = [fid for fid in claim.fact_ids if fid not in facts]
        for fact_id in unknown:
            issues.append(
                ValidationIssue("unknown_fact_id", "critical", fact_id=fact_id, claim_index=index)
            )
        support = [facts[fid] for fid in claim.fact_ids if fid in facts]

        # Une dent écrite doit être portée par un fait d'appui (ex. 26 corrigé en 27).
        cited_teeth = set(TOOTH_IN_TEXT.findall(claim.text))
        supported_teeth = {tooth for fact in support for tooth in fact.teeth}
        if cited_teeth - supported_teeth:
            issues.append(ValidationIssue("tooth_not_supported", "critical", claim_index=index))

        # « Réalisé » exige un fait réalisé (test G).
        if claim.text.startswith("Réalisé") and not any(
            fact.clinical_status == "performed" for fact in support
        ):
            issues.append(ValidationIssue("performed_not_supported", "critical", claim_index=index))

        # Un fait nié rédigé avec les mots dits : la phrase doit dire l'absence. Sinon,
        # le praticien relit — le texte n'est ni corrigé ni bloqué à sa place.
        if any(fact.assertion == "absent" for fact in support) and not negation_ecrite(claim.text):
            issues.append(ValidationIssue("negation_unclear", "review", claim_index=index))

        if claim.text.startswith(UNRENDERED_PREFIX):
            issues.append(ValidationIssue("unrendered_concept", "review", claim_index=index))

    if document.document_type == "operative_note":
        # §45 : un champ important resté vide se signale, il ne se remplit jamais.
        for procedure in encounter.procedures:
            for slot in missing_important_slots(procedure, list(encounter.facts)):
                issues.append(
                    ValidationIssue(
                        "operative_field_missing",
                        "review",
                        fact_id=f"{procedure.procedure_id}:{slot.key}",
                    )
                )

    if document.document_type == "consultation_note":
        rendered = set(document.supported_fact_ids)
        for fact_id in facts:
            if fact_id not in rendered:
                issues.append(ValidationIssue("fact_not_rendered", "review", fact_id=fact_id))

    return issues
