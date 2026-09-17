"""Deepgram Nova-3 : transcription de fichier et temps réel (WebSocket).

Documentation : developers.deepgram.com (listen pre-recorded, listen streaming, keyterm).
"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncIterator
from typing import Any
from urllib.parse import urlencode

import httpx
import websockets

from oris_api.domain.types import AudioChunk, GlossaryHint, TranscriptionResult
from oris_api.providers.base import ProviderInfo, StreamEvent, TranscriptionUnavailable
from oris_api.stt.audio import SAMPLE_RATE, concatenate, pcm_to_wav
from oris_api.stt.common import glossary_terms, segment

MODEL = "nova-3"


def language_code(locale: str) -> str:
    return locale.split("-")[0]  # fr-FR -> fr


class DeepgramPrerecordedProvider:
    info = ProviderInfo(
        name="deepgram", version=f"{MODEL}-prerecorded", capabilities=["diarization", "keyterm"]
    )

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepgram.com",
        use_glossary: bool = True,
        client: httpx.AsyncClient | None = None,
        timeout_s: float = 120,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._use_glossary = use_glossary
        self._client = client
        self._timeout = timeout_s

    def params(
        self, locale: str, glossary: list[GlossaryHint]
    ) -> list[tuple[str, str | int | float | bool | None]]:
        params: list[tuple[str, str | int | float | bool | None]] = [
            ("model", MODEL),
            ("language", language_code(locale)),
            ("diarize", "true"),
            ("punctuate", "true"),
            ("smart_format", "true"),
            ("utterances", "true"),
        ]
        if self._use_glossary:
            params += [("keyterm", term) for term in glossary_terms(glossary)]
        return params

    async def transcribe(
        self, chunks: list[AudioChunk], locale: str, glossary: list[GlossaryHint]
    ) -> TranscriptionResult:
        if not chunks:
            return TranscriptionResult([])
        body = pcm_to_wav(concatenate(chunks))
        client = self._client or httpx.AsyncClient(timeout=self._timeout)
        try:
            response = await client.post(
                f"{self._base_url}/v1/listen",
                params=self.params(locale, glossary),
                headers={"Authorization": f"Token {self._api_key}", "Content-Type": "audio/wav"},
                content=body,
            )
        except httpx.HTTPError as error:
            raise TranscriptionUnavailable("DEEPGRAM_NETWORK") from error
        finally:
            if self._client is None:
                await client.aclose()
        if response.status_code in {401, 403}:
            raise TranscriptionUnavailable("DEEPGRAM_AUTH")
        if response.status_code == 429 or response.status_code >= 500:
            raise TranscriptionUnavailable(f"DEEPGRAM_HTTP_{response.status_code}")
        if response.status_code >= 400:
            raise TranscriptionUnavailable(f"DEEPGRAM_REJECTED_{response.status_code}")
        return self.parse(response.json())

    @staticmethod
    def parse(payload: dict[str, Any]) -> TranscriptionResult:
        utterances = payload.get("results", {}).get("utterances") or []
        segments = []
        labels: dict[str, str] = {}
        for index, utterance in enumerate(u for u in utterances if u.get("transcript", "").strip()):
            item = segment(
                index,
                round(float(utterance["start"]) * 1000),
                round(float(utterance["end"]) * 1000),
                utterance["transcript"],
                utterance.get("confidence"),
            )
            segments.append(item)
            if utterance.get("speaker") is not None:
                labels[item.segment_id] = str(utterance["speaker"])
        return TranscriptionResult(
            segments=segments,
            speaker_labels=labels,
            provider_request_id=payload.get("metadata", {}).get("request_id"),
        )


class DeepgramStreamingProvider:
    """WebSocket temps réel.

    Après une coupure, la connexion est rouverte et l'audio non encore couvert par un
    résultat final est **renvoyé** (rien n'est perdu ; quelques mots peuvent apparaître
    deux fois en résultat intermédiaire). Au-delà de `max_reconnects`, échec explicite.
    """

    info = ProviderInfo(
        name="deepgram",
        version=f"{MODEL}-streaming",
        capabilities=["interim", "diarization", "keyterm"],
    )

    def __init__(
        self,
        api_key: str,
        base_url: str = "wss://api.deepgram.com",
        use_glossary: bool = True,
        max_reconnects: int = 3,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._use_glossary = use_glossary
        self._max_reconnects = max_reconnects

    def url(self, locale: str, glossary: list[GlossaryHint]) -> str:
        params = [
            ("model", MODEL),
            ("language", language_code(locale)),
            ("encoding", "linear16"),
            ("sample_rate", str(SAMPLE_RATE)),
            ("channels", "1"),
            ("interim_results", "true"),
            ("diarize", "true"),
            ("punctuate", "true"),
            ("smart_format", "true"),
        ]
        if self._use_glossary:
            params += [("keyterm", term) for term in glossary_terms(glossary)]
        return f"{self._base_url}/v1/listen?{urlencode(params)}"

    async def stream(
        self, chunks: AsyncIterator[AudioChunk], locale: str, glossary: list[GlossaryHint]
    ) -> AsyncIterator[StreamEvent]:
        source: list[AudioChunk] = []
        done = asyncio.Event()
        arrived = asyncio.Event()

        async def read() -> None:
            async for chunk in chunks:
                source.append(chunk)
                arrived.set()
            done.set()
            arrived.set()

        async def send(ws: Any, start: int, offset: list[int]) -> None:
            index = start
            while True:
                if index < len(source):
                    if index == start:
                        offset[0] = source[start].timestamp_ms
                    await ws.send(source[index].payload)
                    index += 1
                elif done.is_set():
                    await ws.send(json.dumps({"type": "Finalize"}))
                    await ws.send(json.dumps({"type": "CloseStream"}))
                    return
                else:
                    arrived.clear()
                    if index >= len(source) and not done.is_set():
                        await arrived.wait()

        reader = asyncio.create_task(read())
        acknowledged = 0  # premier segment audio pas encore couvert par un résultat final
        attempts = 0
        finals = 0
        headers = {"Authorization": f"Token {self._api_key}"}
        try:
            while True:
                offset = [0]
                start = acknowledged
                sender: asyncio.Task[None] | None = None
                try:
                    async with websockets.connect(
                        self.url(locale, glossary), additional_headers=headers
                    ) as ws:
                        if attempts:
                            yield StreamEvent("reconnected", None, None, 0, time.monotonic())
                        sender = asyncio.create_task(send(ws, start, offset))
                        async for raw in ws:
                            event = self.parse_result(json.loads(raw), finals, offset[0])
                            if event is None:
                                continue
                            if event.kind == "final":
                                finals += 1
                                while acknowledged < len(source) and (
                                    source[acknowledged].timestamp_ms
                                    + len(source[acknowledged].payload) // 32
                                    <= event.audio_end_ms
                                ):
                                    acknowledged += 1
                            yield event
                        if sender.done() and sender.exception() is None:
                            return
                        raise ConnectionError("fermeture prématurée")
                except (OSError, websockets.WebSocketException) as error:
                    if sender is not None:
                        sender.cancel()
                    attempts += 1
                    if attempts > self._max_reconnects:
                        raise TranscriptionUnavailable("DEEPGRAM_STREAM_LOST") from error
        finally:
            reader.cancel()

    @staticmethod
    def parse_result(
        message: dict[str, Any], segment_index: int, offset_ms: int = 0
    ) -> StreamEvent | None:
        if message.get("type") != "Results":
            return None
        alternatives = message.get("channel", {}).get("alternatives") or []
        if not alternatives or not alternatives[0].get("transcript", "").strip():
            return None
        alternative = alternatives[0]
        start_ms = offset_ms + round(float(message.get("start", 0)) * 1000)
        end_ms = start_ms + round(float(message.get("duration", 0)) * 1000)
        words = alternative.get("words") or []
        speakers = [w.get("speaker") for w in words if w.get("speaker") is not None]
        label = str(max(set(speakers), key=speakers.count)) if speakers else None
        final = bool(message.get("is_final"))
        item = segment(
            segment_index,
            start_ms,
            end_ms,
            alternative["transcript"],
            alternative.get("confidence"),
        )
        return StreamEvent(
            "final" if final else "interim",
            item.model_copy(update={"is_final": final}),
            label,
            end_ms,
            time.monotonic(),
        )
