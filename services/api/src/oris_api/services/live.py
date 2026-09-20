"""Transcription en continu pendant la consultation (spec §11, §14.1).

Ce que ce service **est** : une vue provisoire, pour que le praticien voie qu'Oris
entend, et pour repérer tout de suite un micro muet ou un mot systématiquement mal
compris. Le cadrage appelle ça « vérification technique ».

Ce que ce service **n'est pas**, et ne doit jamais devenir : la source du dossier.
Le cadrage est explicite (§14.1) — « le document clinique final ne doit pas être fondé
uniquement sur la transcription intermédiaire streaming ». Rien de ce qui passe ici
n'entre dans l'objet clinique : la finalisation refait la transcription sur l'audio
complet, avec ponctuation, diarisation et normalisation.

Le chemin durable de l'audio n'est pas touché : les segments continuent d'arriver par
`PUT /audio/chunks/{n}`, avec empreinte et idempotence. Ce service **écoute** ce flux,
il ne le remplace pas. Si le direct tombe, la consultation continue sans lui.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from oris_api.domain.types import AudioChunk, GlossaryHint
from oris_api.providers.base import StreamingSpeechToTextProvider

logger = logging.getLogger("oris.live")

# Ce que le panneau montre : les dernières paroles, pas toute la consultation.
FENETRE = 40


@dataclass
class LiveSegment:
    segment_id: str
    start_ms: int
    end_ms: int
    speaker_role: str
    text: str
    is_final: bool


@dataclass
class LiveSession:
    encounter_id: UUID
    queue: asyncio.Queue[AudioChunk | None]
    provider_name: str
    segments: list[LiveSegment] = field(default_factory=list)
    index: dict[str, int] = field(default_factory=dict)
    state: str = "running"
    error_code: str | None = None
    task: asyncio.Task[None] | None = None
    reconnections: int = 0

    def apply(self, segment: LiveSegment) -> None:
        """Un résultat final remplace l'intermédiaire du même segment, en place."""
        position = self.index.get(segment.segment_id)
        if position is None:
            self.index[segment.segment_id] = len(self.segments)
            self.segments.append(segment)
            return
        if self.segments[position].is_final and not segment.is_final:
            return  # un intermédiaire tardif ne défait pas un final
        self.segments[position] = segment


class LiveTranscription:
    """Registre des consultations écoutées en direct. Une par consultation, au plus."""

    def __init__(self) -> None:
        self._sessions: dict[UUID, LiveSession] = {}
        self._loop: asyncio.AbstractEventLoop | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """La boucle de l'application, prise au démarrage : tout passe par elle."""
        self._loop = loop

    @property
    def ready(self) -> bool:
        return self._loop is not None

    def open(
        self,
        encounter_id: UUID,
        provider: StreamingSpeechToTextProvider,
        locale: str,
        glossary: list[GlossaryHint],
    ) -> LiveSession | None:
        """Ouvre l'écoute en direct. Rend None si elle n'est pas possible : jamais d'erreur.

        Une consultation doit pouvoir se dérouler sans direct. C'est un confort, pas
        une condition.
        """
        loop = self._loop
        if loop is None:
            return None
        existing = self._sessions.get(encounter_id)
        if existing is not None:
            return existing
        session = LiveSession(
            encounter_id=encounter_id,
            queue=asyncio.Queue(),
            provider_name=provider.info.name,
        )
        self._sessions[encounter_id] = session

        async def start() -> None:
            session.task = loop.create_task(self._pump(session, provider, locale, glossary))

        asyncio.run_coroutine_threadsafe(start(), loop).result(timeout=5)
        return session

    async def _pump(
        self,
        session: LiveSession,
        provider: StreamingSpeechToTextProvider,
        locale: str,
        glossary: list[GlossaryHint],
    ) -> None:
        async def chunks() -> Any:
            while True:
                chunk = await session.queue.get()
                if chunk is None:
                    return
                yield chunk

        try:
            async for event in provider.stream(chunks(), locale, glossary):
                if event.kind == "reconnected":
                    session.reconnections += 1
                    continue
                if event.segment is None:
                    continue
                session.apply(
                    LiveSegment(
                        segment_id=event.segment.segment_id,
                        start_ms=event.segment.start_ms,
                        end_ms=event.segment.end_ms,
                        speaker_role=event.segment.speaker_role,
                        text=event.segment.text,
                        is_final=event.kind == "final",
                    )
                )
            session.state = "stopped"
        except asyncio.CancelledError:
            session.state = "stopped"
            raise
        except Exception as error:
            # Le direct tombe ; la consultation, elle, continue. L'écran le dira.
            session.state = "failed"
            session.error_code = type(error).__name__
            logger.warning(
                "live.failed",
                extra={"encounter_id": str(session.encounter_id), "error": str(error)},
            )

    def feed(self, encounter_id: UUID, chunk: AudioChunk) -> None:
        """Pousse un segment déjà reçu et stocké. N'échoue jamais bruyamment."""
        session = self._sessions.get(encounter_id)
        loop = self._loop
        if session is None or loop is None or session.state != "running":
            return
        loop.call_soon_threadsafe(session.queue.put_nowait, chunk)

    def close(self, encounter_id: UUID) -> None:
        session = self._sessions.pop(encounter_id, None)
        loop = self._loop
        if session is None or loop is None:
            return
        loop.call_soon_threadsafe(session.queue.put_nowait, None)

    def snapshot(self, encounter_id: UUID) -> LiveSession | None:
        return self._sessions.get(encounter_id)

    def shutdown(self) -> None:
        for encounter_id in list(self._sessions):
            self.close(encounter_id)
