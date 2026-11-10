"""Le dossier se prépare pendant que le praticien passe au patient suivant.

Franck, le 10/11/2026, entre deux patients : « Oris prépare le dossier, c'est très long
parfois et ça m'empêche d'enchaîner ». La fin d'écoute attendait tout le traitement avant
de répondre. Ces essais tiennent les deux moitiés : la réponse part dès que l'écoute est
fermée, et le dossier arrive quand même au bout.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from oris_api.db.models import Encounter
from oris_api.main import app
from oris_api.services import encounters
from oris_api.services.identity import Actor


def en_ecoute(api: Any) -> str:
    cas = api.get("/synthetic-cases").json()[0]["case_id"]
    patient = api.post("/patients", json={"first_name": "Anne", "last_name": "TEST"}).json()
    rencontre = api.post(
        "/encounters", json={"patient_id": patient["id"], "synthetic_case_id": cas}
    ).json()
    api.post(f"/encounters/{rencontre['id']}/start", json={"patient_informed": True})
    return str(rencontre["id"])


def test_l_ecoute_fermee_rend_la_main_puis_le_dossier_arrive(
    api: Any, migrated_engine: Engine
) -> None:
    identifiant = en_ecoute(api)
    with Session(migrated_engine) as session:
        rencontre = session.get(Encounter, identifiant)
        assert rencontre is not None
        acteur = Actor(rencontre.organization_id, rencontre.practitioner_id)
        encounters.finish(
            session, acteur, rencontre, app.state.providers, app.state.audio_sink, differe=True
        )
        session.commit()
        # La main est rendue ici : l'écoute est fermée, rien n'est encore rédigé.
        assert rencontre.status == "finalizing"

    fil = encounters.traiter_en_arriere_plan(
        migrated_engine, acteur, UUID(identifiant), app.state.providers, app.state.audio_sink
    )
    fil.join(timeout=60)
    assert not fil.is_alive()

    lue = api.get(f"/encounters/{identifiant}").json()
    assert lue["status"] == "review"
    assert lue["documents"], "le dossier doit être rédigé, même préparé en arrière-plan"


def test_un_traitement_qui_casse_ne_laisse_pas_la_consultation_en_attente(
    api: Any, migrated_engine: Engine, monkeypatch: Any
) -> None:
    identifiant = en_ecoute(api)
    with Session(migrated_engine) as session:
        rencontre = session.get(Encounter, identifiant)
        assert rencontre is not None
        acteur = Actor(rencontre.organization_id, rencontre.practitioner_id)
        encounters.finish(
            session, acteur, rencontre, app.state.providers, app.state.audio_sink, differe=True
        )
        session.commit()

    def casse(*_: Any, **__: Any) -> None:
        raise RuntimeError("panne")

    monkeypatch.setattr(encounters, "process", casse)
    fil = encounters.traiter_en_arriere_plan(
        migrated_engine, acteur, UUID(identifiant), app.state.providers, app.state.audio_sink
    )
    fil.join(timeout=30)

    lue = api.get(f"/encounters/{identifiant}").json()
    assert lue["status"] == "generation_failed"
    assert lue["processing_errors"][0]["rule"] == "EXTRACTION_UNAVAILABLE"
