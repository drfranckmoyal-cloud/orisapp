"""Registre des versions d'invite, de modèle et de jeu de données (spec §202, §205).

Trois idées, et rien de plus :

- **enregistrer ce qui a servi** : quand une consigne ou un modèle est employé, sa
  version est inscrite une fois pour toutes. Un résultat obtenu il y a six mois peut
  donc être rattaché à la consigne exacte qui l'a produit ;
- **mesurer sans mentir** : une mesure cite le jeu de données et dit s'il est joué ou
  réel ; une porte de sortie ne s'ouvre pas sur une moyenne agréable ;
- **ne jamais écrire de contenu patient** : ces tables ne reçoivent que des versions,
  des durées et des compteurs.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from oris_api.db.models import (
    DatasetVersion,
    EvaluationRun,
    ModelRun,
    ModelVersion,
    PromptVersion,
)


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def prompt_version(
    session: Session,
    component: str,
    version: str,
    text: str,
    parameters: dict[str, str] | None = None,
) -> PromptVersion:
    """Inscrit la consigne si elle est nouvelle, et la rend sinon.

    Si le texte a changé sans que la version change, c'est une erreur de discipline :
    l'empreinte est mise à jour **et** la ligne le dira, mais rien n'est effacé.
    """
    row = session.execute(
        select(PromptVersion).where(
            PromptVersion.component == component, PromptVersion.version == version
        )
    ).scalar_one_or_none()
    empreinte = content_hash(text)
    if row is None:
        row = PromptVersion(
            component=component,
            version=version,
            content_hash=empreinte,
            parameters=parameters or {},
        )
        session.add(row)
        session.flush()
        return row
    if row.content_hash != empreinte:
        row.content_hash = empreinte
        session.flush()
    return row


def model_version(
    session: Session,
    component: str,
    provider: str,
    model_id: str,
    parameters: dict[str, str] | None = None,
) -> ModelVersion:
    row = session.execute(
        select(ModelVersion).where(
            ModelVersion.component == component,
            ModelVersion.provider == provider,
            ModelVersion.model_id == model_id,
        )
    ).scalar_one_or_none()
    if row is None:
        row = ModelVersion(
            component=component,
            provider=provider,
            model_id=model_id,
            parameters=parameters or {},
        )
        session.add(row)
        session.flush()
    return row


def dataset_version(
    session: Session,
    name: str,
    version: str,
    item_count: int,
    checksum: str = "",
    nature: str = "synthetic",
    description: str = "",
) -> DatasetVersion:
    row = session.execute(
        select(DatasetVersion).where(DatasetVersion.name == name, DatasetVersion.version == version)
    ).scalar_one_or_none()
    if row is None:
        row = DatasetVersion(
            name=name,
            version=version,
            item_count=item_count,
            checksum=checksum,
            nature=nature,
            description=description,
        )
        session.add(row)
        session.flush()
    return row


def record_evaluation(
    session: Session,
    component: str,
    candidate_version: str,
    dataset: str,
    metrics: dict[str, float],
    critical_regressions: list[str],
) -> EvaluationRun:
    """Une mesure passe la porte seulement si aucune régression critique n'est trouvée."""
    row = EvaluationRun(
        component=component,
        candidate_version=candidate_version,
        dataset_version=dataset,
        metrics=dict(metrics),
        critical_regressions=list(critical_regressions),
        release_gate_passed=not critical_regressions,
    )
    session.add(row)
    session.flush()
    return row


@dataclass
class RunTimer:
    """Mesure la durée d'un appel fournisseur, sans jamais toucher à son contenu."""

    component: str
    encounter_id: UUID | None
    started: datetime

    def elapsed_ms(self) -> int:
        return round((datetime.now(UTC) - self.started).total_seconds() * 1000)


def start_run(component: str, encounter_id: UUID | None) -> RunTimer:
    return RunTimer(component=component, encounter_id=encounter_id, started=datetime.now(UTC))


def finish_run(
    session: Session,
    timer: RunTimer,
    *,
    status: str = "succeeded",
    error_code: str | None = None,
    counters: dict[str, int] | None = None,
    model_version_id: UUID | None = None,
    prompt_version_id: UUID | None = None,
) -> ModelRun:
    """Trace l'appel. `counters` ne contient que des nombres : jamais un extrait."""
    row = ModelRun(
        encounter_id=timer.encounter_id,
        component=timer.component,
        model_version_id=model_version_id,
        prompt_version_id=prompt_version_id,
        status=status,
        error_code=error_code,
        latency_ms=timer.elapsed_ms(),
        counters=dict(counters or {}),
    )
    session.add(row)
    session.flush()
    return row


def runs_for(session: Session, encounter_id: UUID) -> list[ModelRun]:
    return list(
        session.scalars(
            select(ModelRun)
            .where(ModelRun.encounter_id == encounter_id)
            .order_by(ModelRun.created_at)
        )
    )
