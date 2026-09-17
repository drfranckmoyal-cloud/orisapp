"""Azure AI Speech : transcription rapide (fichier) et temps réel (SDK, diarisation).

Documentation : learn.microsoft.com, « fast transcription » (api-version 2025-10-15) et
« real-time diarization » (ConversationTranscriber).
"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncIterator
from typing import Any

import httpx

from oris_api.domain.types import AudioChunk, GlossaryHint, TranscriptionResult
from oris_api.providers.base import ProviderInfo, StreamEvent, TranscriptionUnavailable
from oris_api.stt.audio import SAMPLE_RATE, concatenate, pcm_to_wav
from oris_api.stt.common import glossary_terms, segment

API_VERSION = "2025-10-15"
TICKS_PER_MS = 10_000


class AzureFastTranscriptionProvider:
    info = ProviderInfo(
        name="azure_speech",
        version=f"fast-{API_VERSION}",
        capabilities=["diarization", "phrase_list"],
    )

    def __init__(
        self,
        api_key: str,
        endpoint: str,
        use_glossary: bool = True,
        max_speakers: int = 4,
        client: httpx.AsyncClient | None = None,
        timeout_s: float = 300,
    ) -> None:
        self._api_key = api_key
        self._endpoint = endpoint.rstrip("/")
        self._use_glossary = use_glossary
        self._max_speakers = max_speakers
        self._client = client
        self._timeout = timeout_s

    def definition(self, locale: str, glossary: list[GlossaryHint]) -> dict[str, Any]:
        definition: dict[str, Any] = {
            "locales": [locale],
            "diarization": {"enabled": True, "maxSpeakers": self._max_speakers},
            "profanityFilterMode": "None",
        }
        if self._use_glossary:
            definition["phraseList"] = {"phrases": glossary_terms(glossary)}
        return definition

    async def transcribe(
        self, chunks: list[AudioChunk], locale: str, glossary: list[GlossaryHint]
    ) -> TranscriptionResult:
        if not chunks:
            return TranscriptionResult([])
        client = self._client or httpx.AsyncClient(timeout=self._timeout)
        try:
            response = await client.post(
                f"{self._endpoint}/speechtotext/transcriptions:transcribe",
                params={"api-version": API_VERSION},
                headers={"Ocp-Apim-Subscription-Key": self._api_key},
                files={
                    "audio": ("consultation.wav", pcm_to_wav(concatenate(chunks)), "audio/wav"),
                    "definition": (
                        None,
                        json.dumps(self.definition(locale, glossary)),
                        "application/json",
                    ),
                },
            )
        except httpx.HTTPError as error:
            raise TranscriptionUnavailable("AZURE_NETWORK") from error
        finally:
            if self._client is None:
                await client.aclose()
        if response.status_code in {401, 403}:
            raise TranscriptionUnavailable("AZURE_AUTH")
        if response.status_code == 429 or response.status_code >= 500:
            raise TranscriptionUnavailable(f"AZURE_HTTP_{response.status_code}")
        if response.status_code >= 400:
            raise TranscriptionUnavailable(f"AZURE_REJECTED_{response.status_code}")
        return self.parse(response.json(), response.headers.get("apim-request-id"))

    @staticmethod
    def parse(payload: dict[str, Any], request_id: str | None = None) -> TranscriptionResult:
        segments = []
        labels: dict[str, str] = {}
        phrases = [p for p in payload.get("phrases") or [] if str(p.get("text", "")).strip()]
        for index, phrase in enumerate(
            sorted(phrases, key=lambda p: p.get("offsetMilliseconds", 0))
        ):
            start = int(phrase.get("offsetMilliseconds", 0))
            item = segment(
                index,
                start,
                start + int(phrase.get("durationMilliseconds", 0)),
                phrase["text"],
                phrase.get("confidence"),
            )
            segments.append(item)
            if phrase.get("speaker") is not None:
                labels[item.segment_id] = str(phrase["speaker"])
        return TranscriptionResult(
            segments=segments, speaker_labels=labels, provider_request_id=request_id
        )


class AzureStreamingProvider:
    """Temps réel via le SDK Speech (ConversationTranscriber, flux poussé, diarisation)."""

    info = ProviderInfo(
        name="azure_speech",
        version="sdk-conversation-transcriber",
        capabilities=["interim", "diarization", "phrase_list"],
    )

    def __init__(self, api_key: str, endpoint: str, use_glossary: bool = True) -> None:
        self._api_key = api_key
        self._endpoint = endpoint.rstrip("/")
        self._use_glossary = use_glossary

    async def stream(
        self, chunks: AsyncIterator[AudioChunk], locale: str, glossary: list[GlossaryHint]
    ) -> AsyncIterator[StreamEvent]:
        import azure.cognitiveservices.speech as speechsdk

        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[StreamEvent | BaseException | None] = asyncio.Queue()
        config = speechsdk.SpeechConfig(subscription=self._api_key, endpoint=self._endpoint)
        config.speech_recognition_language = locale
        config.set_property(
            speechsdk.PropertyId.SpeechServiceResponse_DiarizeIntermediateResults, "true"
        )
        audio_format = speechsdk.audio.AudioStreamFormat(
            samples_per_second=SAMPLE_RATE, bits_per_sample=16, channels=1
        )
        push = speechsdk.audio.PushAudioInputStream(stream_format=audio_format)
        transcriber = speechsdk.transcription.ConversationTranscriber(
            speech_config=config, audio_config=speechsdk.audio.AudioConfig(stream=push)
        )
        if self._use_glossary:
            phrases = speechsdk.PhraseListGrammar.from_recognizer(transcriber)
            for term in glossary_terms(glossary):
                phrases.addPhrase(term)
        counter = {"final": 0}
        stopped = asyncio.Event()

        def emit(item: StreamEvent | BaseException | None) -> None:
            loop.call_soon_threadsafe(queue.put_nowait, item)

        def on_result(kind: str) -> Any:
            def handler(evt: Any) -> None:
                event = self.to_event(kind, evt.result, counter["final"])
                if event is not None:
                    if kind == "final":
                        counter["final"] += 1
                    emit(event)

            return handler

        def on_canceled(evt: Any) -> None:
            details = getattr(evt, "cancellation_details", None)
            if details is not None and str(getattr(details, "reason", "")).endswith("Error"):
                emit(TranscriptionUnavailable("AZURE_STREAM_CANCELED"))
            loop.call_soon_threadsafe(stopped.set)

        transcriber.transcribing.connect(on_result("interim"))
        transcriber.transcribed.connect(on_result("final"))
        transcriber.canceled.connect(on_canceled)
        transcriber.session_stopped.connect(lambda _evt: loop.call_soon_threadsafe(stopped.set))

        async def feed() -> None:
            await asyncio.to_thread(lambda: transcriber.start_transcribing_async().get())
            async for chunk in chunks:
                push.write(chunk.payload)
            push.close()
            await stopped.wait()
            await asyncio.to_thread(lambda: transcriber.stop_transcribing_async().get())
            emit(None)

        feeder = asyncio.create_task(feed())
        try:
            while (item := await queue.get()) is not None:
                if isinstance(item, BaseException):
                    raise item
                yield item
        finally:
            feeder.cancel()

    @staticmethod
    def to_event(kind: str, result: Any, index: int) -> StreamEvent | None:
        text = str(getattr(result, "text", "") or "").strip()
        if not text:
            return None
        start_ms = int(getattr(result, "offset", 0)) // TICKS_PER_MS
        end_ms = start_ms + int(getattr(result, "duration", 0)) // TICKS_PER_MS
        speaker = getattr(result, "speaker_id", None)
        label = None if speaker in (None, "", "Unknown") else str(speaker)
        item = segment(index, start_ms, end_ms, text, None).model_copy(
            update={"is_final": kind == "final"}
        )
        return StreamEvent(kind, item, label, end_ms, time.monotonic())  # type: ignore[arg-type]
