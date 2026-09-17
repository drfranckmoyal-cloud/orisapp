"""Corrections cliniques structurées (spec §46–48, D016).

Une correction est un patch sur l'objet clinique, jamais une retouche de texte.
`apply_operations` est pure : objet v(n) + opérations -> objet v(n+1) et
brouillons de LearningEvents. La persistance, l'invalidation des documents et
la régénération sont faites par le service appelant.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from oris_api.contracts import ClinicalEncounter, ClinicalFact
from oris_api.contracts.generated import (
    ClinicalFactAssertion,
    ClinicalFactCategory,
    ClinicalFactCertainty,
    ClinicalFactClinicalStatus,
    ClinicalFactSurfaces,
    ClinicalFactTemporality,
    LearningEventEventType,
    TreatmentPlanItemStatus,
)

FdiTooth = Annotated[
    str, Field(pattern=r"^(?:1[1-8]|2[1-8]|3[1-8]|4[1-8]|5[1-5]|6[1-5]|7[1-5]|8[1-5])$")
]
TREATMENT_CATEGORIES = frozenset({"treatment_option", "treatment_decision", "procedure"})
PLAN_TO_FACT_STATUS = {
    "discussed": "discussed",
    "proposed": "proposed",
    "accepted": "accepted",
    "refused": "refused",
    "deferred": "deferred",
    "planned": "planned",
    "completed": "performed",
}


class ReplaceTooth(BaseModel):
    """« Remplace 26 par 27 » : faits ciblés (tous si omis), plan et actes liés."""

    model_config = ConfigDict(extra="forbid")
    operation: Literal["replace_tooth"]
    from_tooth: FdiTooth
    to_tooth: FdiTooth
    fact_ids: list[str] | None = None


class FactChanges(BaseModel):
    model_config = ConfigDict(extra="forbid")
    assertion: ClinicalFactAssertion | None = None
    temporality: ClinicalFactTemporality | None = None
    clinical_status: ClinicalFactClinicalStatus | None = None
    certainty: ClinicalFactCertainty | None = None
    teeth: list[FdiTooth] | None = None
    value: Any = None


class UpdateFact(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation: Literal["update_fact"]
    fact_id: str
    changes: FactChanges


class SetPlanItemStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation: Literal["set_plan_item_status"]
    item_id: str
    status: TreatmentPlanItemStatus


class NewFact(BaseModel):
    model_config = ConfigDict(extra="forbid")
    category: ClinicalFactCategory
    concept: Annotated[str, Field(min_length=1, max_length=200)]
    value: Any
    teeth: list[FdiTooth] = []
    surfaces: list[ClinicalFactSurfaces] = []
    assertion: ClinicalFactAssertion
    temporality: ClinicalFactTemporality
    clinical_status: ClinicalFactClinicalStatus
    certainty: ClinicalFactCertainty


class AddFact(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation: Literal["add_fact"]
    fact: NewFact


class RemoveFact(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation: Literal["remove_fact"]
    fact_id: str


CorrectionOperation = Annotated[
    ReplaceTooth | UpdateFact | SetPlanItemStatus | AddFact | RemoveFact,
    Field(discriminator="operation"),
]


class CorrectionError(ValueError):
    def __init__(self, code: str, subject_id: str | None = None) -> None:
        self.code = code
        self.subject_id = subject_id
        super().__init__(code if subject_id is None else f"{code}: {subject_id}")


@dataclass(frozen=True)
class LearningEventDraft:
    event_type: LearningEventEventType
    before: dict[str, Any] | None
    after: dict[str, Any] | None
    confidence_before: float | None = None


@dataclass(frozen=True)
class CorrectionResult:
    encounter: ClinicalEncounter
    learning_events: list[LearningEventDraft]


def event_type_for_field(field: str, fact: ClinicalFact) -> LearningEventEventType:
    match field:
        case "teeth":
            return "tooth_number_correction"
        case "assertion":
            return "negation_correction"
        case "temporality":
            return "temporality_correction"
        case "certainty":
            return "certainty_correction"
        case "clinical_status" if fact.category in TREATMENT_CATEGORIES:
            return "treatment_status_correction"
        case _:
            return "clinical_fact_corrected"


def replace_in(teeth: list[str], old: str, new: str) -> list[str]:
    replaced = [new if tooth == old else tooth for tooth in teeth]
    return list(dict.fromkeys(replaced))  # garde l'ordre, sans doublon


def fact_by_id(facts: list[ClinicalFact], fact_id: str) -> ClinicalFact:
    for fact in facts:
        if fact.fact_id == fact_id:
            return fact
    raise CorrectionError("FACT_NOT_FOUND", fact_id)


def apply_operations(
    encounter: ClinicalEncounter, operations: list[CorrectionOperation]
) -> CorrectionResult:
    if not operations:
        raise CorrectionError("NO_OPERATION")
    facts = [fact.model_copy(deep=True) for fact in encounter.facts]
    plan = encounter.treatment_plan.model_copy(deep=True) if encounter.treatment_plan else None
    procedures = [procedure.model_copy(deep=True) for procedure in encounter.procedures]
    events: list[LearningEventDraft] = []

    for operation in operations:
        match operation:
            case ReplaceTooth(from_tooth=old, to_tooth=new, fact_ids=targets):
                if old == new:
                    raise CorrectionError("SAME_TOOTH")
                selected = [
                    f for f in facts if old in f.teeth and (targets is None or f.fact_id in targets)
                ]
                if not selected:
                    raise CorrectionError("TOOTH_NOT_FOUND")
                selected_ids = {f.fact_id for f in selected}
                for fact in selected:
                    events.append(
                        LearningEventDraft(
                            "tooth_number_correction",
                            {"fact_id": fact.fact_id, "concept": fact.concept, "teeth": fact.teeth},
                            {
                                "fact_id": fact.fact_id,
                                "concept": fact.concept,
                                "teeth": replace_in(fact.teeth, old, new),
                            },
                            fact.confidence,
                        )
                    )
                    fact.teeth = replace_in(fact.teeth, old, new)
                    fact.manually_validated = True
                # Le plan et les actes appuyés par ces faits suivent : pas de 26 résiduel.
                for item in plan.items if plan else []:
                    if old in item.teeth and selected_ids & set(item.evidence_fact_ids):
                        item.teeth = replace_in(item.teeth, old, new)
                for procedure in procedures:
                    if old in procedure.teeth and selected_ids & set(procedure.evidence_fact_ids):
                        procedure.teeth = replace_in(procedure.teeth, old, new)

            case UpdateFact(fact_id=fact_id, changes=changes):
                fact = fact_by_id(facts, fact_id)
                provided = changes.model_fields_set
                if not provided:
                    raise CorrectionError("NO_CHANGE", fact_id)
                for field in sorted(provided):
                    before, after = getattr(fact, field), getattr(changes, field)
                    if before == after:
                        continue
                    events.append(
                        LearningEventDraft(
                            event_type_for_field(field, fact),
                            {"fact_id": fact_id, "concept": fact.concept, field: before},
                            {"fact_id": fact_id, "concept": fact.concept, field: after},
                            fact.confidence,
                        )
                    )
                    setattr(fact, field, after)
                fact.manually_validated = True

            case SetPlanItemStatus(item_id=item_id, status=status):
                matches = [i for i in plan.items if i.item_id == item_id] if plan else []
                if not matches:
                    raise CorrectionError("PLAN_ITEM_NOT_FOUND", item_id)
                item = matches[0]
                if item.status != status:
                    events.append(
                        LearningEventDraft(
                            "treatment_status_correction",
                            {"item_id": item_id, "status": item.status},
                            {"item_id": item_id, "status": status},
                        )
                    )
                    item.status = status
                    # La décision du praticien est le fait qui justifie le nouveau statut :
                    # les faits de traitement qui appuient l'élément suivent (spec §34).
                    fact_status = PLAN_TO_FACT_STATUS[status]
                    for fact in facts:
                        if (
                            fact.fact_id in item.evidence_fact_ids
                            and fact.category in TREATMENT_CATEGORIES
                            and fact.clinical_status != fact_status
                        ):
                            fact.clinical_status = fact_status  # type: ignore[assignment]
                            fact.manually_validated = True

            case AddFact(fact=new_fact):
                fact = ClinicalFact(
                    fact_id=f"m-{uuid4().hex[:8]}",
                    **new_fact.model_dump(),
                    speaker_role="manual",
                    source_type="manual",
                    evidence_segment_ids=[],
                    confidence=1.0,
                    manually_validated=True,
                )
                facts.append(fact)
                events.append(
                    LearningEventDraft(
                        "clinical_fact_added",
                        None,
                        {
                            "fact_id": fact.fact_id,
                            "concept": fact.concept,
                            "category": fact.category,
                            "clinical_status": fact.clinical_status,
                        },
                    )
                )

            case RemoveFact(fact_id=fact_id):
                fact = fact_by_id(facts, fact_id)
                referenced = any(
                    fact_id in i.evidence_fact_ids for i in (plan.items if plan else [])
                )
                referenced |= any(fact_id in p.evidence_fact_ids for p in procedures)
                if referenced:
                    raise CorrectionError("FACT_REFERENCED", fact_id)
                facts.remove(fact)
                events.append(
                    LearningEventDraft(
                        "clinical_fact_removed",
                        {"fact_id": fact_id, "concept": fact.concept, "category": fact.category},
                        None,
                        fact.confidence,
                    )
                )

    if not events:
        raise CorrectionError("NO_CHANGE")

    corrected = encounter.model_copy(
        update={
            "facts": facts,
            "treatment_plan": plan,
            "procedures": procedures,
            "object_version": encounter.object_version + 1,
        }
    )
    return CorrectionResult(ClinicalEncounter.model_validate(corrected.model_dump()), events)
