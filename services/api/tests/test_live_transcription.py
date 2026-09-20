"""Écoute en direct pendant la consultation (spec §11, §14.1).

La garantie qui compte n'est pas que le direct marche : c'est qu'il ne **serve** à
rien d'autre qu'à regarder. Le cadrage l'écrit noir sur blanc — le document clinique
final ne doit pas être fondé sur la transcription intermédiaire.
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from dataclasses import replace
from typing import Any

from oris_api.contracts import TranscriptSegment
from oris_api.domain.types import AudioChunk, GlossaryHint
from oris_api.main import app
from oris_api.providers.base import ProviderInfo, StreamEvent
from oris_api.services.live import LiveSegment, LiveSession
from tests.conftest import clinical_object
from tests.test_audio_api import new_encounter, pcm, put_chunk

# Texte que seul le direct produit : s'il apparaît dans le dossier, le test doit tomber.
MARQUEUR = "PAROLE ENTENDUE EN DIRECT"


class DirectDouble:
    """Fournisseur d'écoute en direct : un intermédiaire puis un final par segment audio."""

    info = ProviderInfo(name="double", version="direct-1", capabilities=["interim"])

    def __init__(self, tombe: bool = False) -> None:
        self.tombe = tombe

    async def stream(
        self, chunks: AsyncIterator[AudioChunk], locale: str, glossary: list[GlossaryHint]
    ) -> AsyncIterator[StreamEvent]:
        async for chunk in chunks:
            if self.tombe:
                raise RuntimeError("liaison temps réel perdue")
            base = TranscriptSegment(
                segment_id=f"direct-{chunk.sequence}",
                start_ms=chunk.timestamp_ms,
                end_ms=chunk.timestamp_ms + 2000,
                speaker_role="practitioner",
                text=f"{MARQUEUR} {chunk.sequence}",
                confidence=0.5,
                is_final=False,
            )
            yield StreamEvent("interim", base.model_copy(update={"text": "PAROLE…"}), None, 0, 0.0)
            yield StreamEvent("final", base.model_copy(update={"is_final": True}), None, 0, 0.0)


def with_live(double: DirectDouble | None) -> Any:
    original = app.state.providers
    app.state.providers = replace(original, live_speech_to_text=double)
    return original


def attendre(api: Any, eid: str, combien: int, essais: int = 40) -> dict[str, Any]:
    """Le direct vit dans la boucle de l'application : on lui laisse le temps de tourner."""
    for _ in range(essais):
        vue: dict[str, Any] = api.get(f"/encounters/{eid}/live").json()
        if vue["total"] >= combien:
            return vue
        time.sleep(0.05)
    dernier: dict[str, Any] = api.get(f"/encounters/{eid}/live").json()
    return dernier


def test_the_live_view_is_off_unless_it_is_turned_on(api: Any) -> None:
    """Drapeau baissé (§85) : l'écran doit le dire, pas faire semblant."""
    eid = new_encounter(api)
    assert api.get(f"/encounters/{eid}/live").json() == {
        "state": "disabled",
        "error_code": None,
        "segments": [],
        "total": 0,
        "reconnections": 0,
    }


def test_words_appear_as_they_are_heard_and_settle(api: Any) -> None:
    original = with_live(DirectDouble())
    try:
        eid = new_encounter(api)
        put_chunk(api, eid, 0, pcm())
        vue = attendre(api, eid, 1)
        assert vue["state"] == "running"
        assert vue["total"] == 1
        # Le final a remplacé l'intermédiaire à la même place : pas deux lignes.
        segment = vue["segments"][0]
        assert segment["is_final"] is True
        assert segment["text"] == f"{MARQUEUR} 0"

        put_chunk(api, eid, 1, pcm(seed=2))
        assert attendre(api, eid, 2)["total"] == 2
    finally:
        app.state.providers = original


def test_nothing_heard_live_ever_reaches_the_record(api: Any) -> None:
    """§14.1 : le dossier est refait sur l'audio complet, jamais repris du direct."""
    original = with_live(DirectDouble())
    try:
        eid = new_encounter(api)
        put_chunk(api, eid, 0, pcm())
        assert MARQUEUR in attendre(api, eid, 1)["segments"][0]["text"]

        # Fin de consultation : la transcription du dossier vient du fournisseur d'après
        # coup, qui ne connaît pas ce marqueur.
        api.post(f"/encounters/{eid}/finish", json={"accept_gaps": True})

        segments = api.get(f"/encounters/{eid}/transcript").json()["segments"]
        assert all(MARQUEUR not in segment["text"] for segment in segments)
        assert all(not segment["segment_id"].startswith("direct-") for segment in segments)

        statut = api.get(f"/encounters/{eid}").json()["status"]
        if statut == "review":
            objet = clinical_object(api, eid)
            assert all(MARQUEUR not in str(fact.get("value", "")) for fact in objet["facts"])
            for fact in objet["facts"]:
                assert all(not e.startswith("direct-") for e in fact["evidence_segment_ids"])
    finally:
        app.state.providers = original


def test_the_consultation_survives_a_broken_live_link(api: Any) -> None:
    """Le direct est un confort. Sa panne ne doit pas coûter une consultation."""
    original = with_live(DirectDouble(tombe=True))
    try:
        eid = new_encounter(api)
        assert put_chunk(api, eid, 0, pcm()).status_code == 201

        for _ in range(40):
            vue = api.get(f"/encounters/{eid}/live").json()
            if vue["state"] == "failed":
                break
            time.sleep(0.05)
        assert vue["state"] == "failed"
        assert vue["error_code"] == "RuntimeError"

        # L'audio, lui, est bien arrivé : la consultation se termine normalement.
        assert api.get(f"/encounters/{eid}/audio").json()["received_count"] == 1
        assert api.post(f"/encounters/{eid}/finish", json={"accept_gaps": True}).status_code == 200
    finally:
        app.state.providers = original


def test_the_live_stops_when_the_consultation_ends(api: Any) -> None:
    original = with_live(DirectDouble())
    try:
        eid = new_encounter(api)
        put_chunk(api, eid, 0, pcm())
        attendre(api, eid, 1)
        api.post(f"/encounters/{eid}/finish", json={"accept_gaps": True})
        # Plus de session : l'écoute est close, rien ne continue en arrière-plan.
        assert api.get(f"/encounters/{eid}/live").json()["state"] == "idle"
    finally:
        app.state.providers = original


def test_a_late_interim_never_undoes_a_final() -> None:
    """Règle d'assemblage : ce qui est acquis ne redevient pas flou."""
    import asyncio

    session = LiveSession(
        encounter_id=__import__("uuid").uuid4(), queue=asyncio.Queue(), provider_name="test"
    )
    session.apply(LiveSegment("s1", 0, 1000, "practitioner", "sur la vingt…", False))
    session.apply(LiveSegment("s1", 0, 1000, "practitioner", "sur la vingt-six.", True))
    session.apply(LiveSegment("s1", 0, 1000, "practitioner", "sur la vingt…", False))
    assert [(s.text, s.is_final) for s in session.segments] == [("sur la vingt-six.", True)]
