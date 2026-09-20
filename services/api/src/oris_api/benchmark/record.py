"""Enregistre une mesure du banc d'essai dans la base (spec §202, §205).

Un rapport dans un fichier se perd ; une ligne en base se compare. Le jeu de données
et la mesure sont inscrits ensemble : une note sans jeu de données ne veut rien dire.

Si la base n'est pas joignable, la mesure n'est pas perdue pour autant : le rapport
fichier reste écrit, et l'échec est dit à voix haute — jamais avalé en silence.
"""

from __future__ import annotations

import logging

from oris_api.db.session import get_engine
from oris_api.services import registry

logger = logging.getLogger("oris.benchmark")


def record(
    *,
    component: str,
    candidate_version: str,
    dataset_name: str,
    dataset_version: str,
    item_count: int,
    metrics: dict[str, float],
    critical_regressions: list[str],
    nature: str = "synthetic",
) -> bool:
    """Rend True si la mesure a été inscrite. N'interrompt jamais le banc d'essai."""
    from sqlalchemy.orm import sessionmaker

    try:
        factory = sessionmaker(bind=get_engine(), expire_on_commit=False)
        with factory() as session:
            registry.dataset_version(
                session,
                dataset_name,
                dataset_version,
                item_count=item_count,
                nature=nature,
            )
            registry.record_evaluation(
                session,
                component=component,
                candidate_version=candidate_version,
                dataset=f"{dataset_name}@{dataset_version}",
                metrics=metrics,
                critical_regressions=critical_regressions,
            )
            session.commit()
        return True
    except Exception as error:  # la mesure compte plus que son archivage
        logger.warning("benchmark.not_recorded", extra={"error": str(error)})
        print(f"Mesure non archivée en base ({error}). Le rapport fichier est écrit.")
        return False
