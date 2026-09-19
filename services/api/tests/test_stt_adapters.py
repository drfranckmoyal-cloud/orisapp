"""Adaptateurs Deepgram et Azure, sans réseau : requêtes construites et réponses traduites."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from types import SimpleNamespace
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
import websockets

from oris_api.domain.types import AudioChunk
from oris_api.providers.base import TranscriptionUnavailable
from oris_api.stt.audio import split_pcm, wav_to_pcm
from oris_api.stt.azure_speech import AzureFastTranscriptionProvider, AzureStreamingProvider
from oris_api.stt.deepgram import DeepgramPrerecordedProvider, DeepgramStreamingProvider

PCM = b"\x01\x00" * 16_000 * 5  # 5 s


def chunks() -> list[AudioChunk]:
    return split_pcm(PCM, "session")


DEEPGRAM_RESPONSE = {
    "metadata": {"request_id": "req-1", "duration": 5.0},
    "results": {
        "utterances": [
            {
                "start": 2.5,
                "end": 4.0,
                "confidence": 0.91,
                "channel": 0,
                "transcript": "Pas de douleur nocturne.",
                "speaker": 1,
                "id": "b",
                "words": [],
            },
            {
                "start": 0.1,
                "end": 2.3,
                "confidence": 0.95,
                "channel": 0,
                "transcript": "Sur la 27, restauration fracturée.",
                "speaker": 0,
                "id": "a",
                "words": [],
            },
            {
                "start": 4.1,
                "end": 4.2,
                "confidence": 0.2,
                "channel": 0,
                "transcript": "  ",
                "speaker": 0,
                "id": "c",
                "words": [],
            },
        ]
    },
}


def test_deepgram_request_and_parsing() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = request.url
        seen["headers"] = request.headers
        seen["body"] = request.content
        return httpx.Response(200, json=DEEPGRAM_RESPONSE)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = DeepgramPrerecordedProvider("secret", client=client)
    result = asyncio.run(provider.transcribe(chunks(), "fr-FR", []))

    query = parse_qs(urlparse(str(seen["url"])).query)
    assert str(seen["url"]).startswith("https://api.deepgram.com/v1/listen?")
    assert query["model"] == ["nova-3"] and query["language"] == ["fr"]
    assert query["diarize"] == ["true"] and query["utterances"] == ["true"]
    assert "Filtek Supreme XTE" in query["keyterm"] and len(query["keyterm"]) <= 50
    assert seen["headers"]["authorization"] == "Token secret"
    assert wav_to_pcm(seen["body"]) == (PCM, 16_000)

    # Utterances vides écartées, ordre de réponse conservé, étiquettes de locuteur séparées.
    assert [s.text for s in result.segments] == [
        "Pas de douleur nocturne.",
        "Sur la 27, restauration fracturée.",
    ]
    assert [(s.start_ms, s.end_ms) for s in result.segments] == [(2500, 4000), (100, 2300)]
    assert {s.speaker_role for s in result.segments} == {"unknown"}
    assert result.speaker_labels == {"t1": "1", "t2": "0"}
    assert result.provider_request_id == "req-1"


def test_deepgram_without_glossary_sends_no_keyterm() -> None:
    provider = DeepgramPrerecordedProvider("secret", use_glossary=False)
    assert "keyterm" not in dict(provider.params("fr-FR", []))


@pytest.mark.parametrize(
    ("status", "code"),
    [(401, "DEEPGRAM_AUTH"), (503, "DEEPGRAM_HTTP_503"), (429, "DEEPGRAM_HTTP_429")],
)
def test_deepgram_errors_are_explicit(status: int, code: str) -> None:
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _r: httpx.Response(status, json={}))
    )
    with pytest.raises(TranscriptionUnavailable) as caught:
        asyncio.run(
            DeepgramPrerecordedProvider("k", client=client, retry_backoff_s=(0.0, 0.0)).transcribe(
                chunks(), "fr-FR", []
            )
        )
    assert caught.value.code == code


def test_network_failure_is_transient() -> None:
    def fail(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    client = httpx.AsyncClient(transport=httpx.MockTransport(fail))
    with pytest.raises(TranscriptionUnavailable) as caught:
        asyncio.run(
            DeepgramPrerecordedProvider("k", client=client, retry_backoff_s=(0.0, 0.0)).transcribe(
                chunks(), "fr-FR", []
            )
        )
    assert caught.value.code == "DEEPGRAM_NETWORK"


AZURE_RESPONSE = {
    "durationMilliseconds": 5000,
    "combinedPhrases": [{"channel": 0, "text": "..."}],
    "phrases": [
        {
            "channel": 0,
            "speaker": 2,
            "offsetMilliseconds": 2600,
            "durationMilliseconds": 1400,
            "text": "Je n'ai pas mal.",
            "words": [],
            "locale": "fr-FR",
            "confidence": 0.88,
        },
        {
            "channel": 0,
            "speaker": 1,
            "offsetMilliseconds": 120,
            "durationMilliseconds": 2200,
            "text": "Composite réalisé sur 11.",
            "words": [],
            "locale": "fr-FR",
            "confidence": 0.93,
        },
    ],
}


def test_azure_fast_transcription_request_and_parsing() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["request"] = request
        return httpx.Response(200, json=AZURE_RESPONSE, headers={"apim-request-id": "az-1"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = AzureFastTranscriptionProvider(
        "secret", "https://oris.cognitiveservices.azure.com/", client=client
    )
    result = asyncio.run(provider.transcribe(chunks(), "fr-FR", []))

    request: httpx.Request = seen["request"]
    assert request.url.path == "/speechtotext/transcriptions:transcribe"
    assert request.url.params["api-version"] == "2025-10-15"
    assert request.headers["ocp-apim-subscription-key"] == "secret"
    body = request.content
    assert b'name="audio"' in body and b"RIFF" in body
    definition = json.loads(
        body.split(b'name="definition"')[1].split(b"\r\n\r\n", 1)[1].split(b"\r\n--")[0]
    )
    assert definition["locales"] == ["fr-FR"]
    assert definition["diarization"] == {"enabled": True, "maxSpeakers": 4}
    assert "Scotchbond Universal Plus" in definition["phraseList"]["phrases"]

    assert [s.text for s in result.segments] == ["Composite réalisé sur 11.", "Je n'ai pas mal."]
    assert [(s.start_ms, s.end_ms) for s in result.segments] == [(120, 2320), (2600, 4000)]
    assert result.speaker_labels == {"t1": "1", "t2": "2"}
    assert result.provider_request_id == "az-1"


def test_azure_without_glossary_has_no_phrase_list() -> None:
    provider = AzureFastTranscriptionProvider("k", "https://x", use_glossary=False)
    assert "phraseList" not in provider.definition("fr-FR", [])


def test_azure_streaming_event_mapping() -> None:
    result = SimpleNamespace(
        text="Pas de douleur au froid.",
        offset=12_000_000,
        duration=15_000_000,
        speaker_id="Guest-2",
    )
    event = AzureStreamingProvider.to_event("final", result, 3)
    assert event is not None
    assert (event.kind, event.audio_end_ms, event.speaker_label) == ("final", 2700, "Guest-2")
    assert event.segment is not None and event.segment.start_ms == 1200 and event.segment.is_final
    unknown = SimpleNamespace(text="Pas", offset=0, duration=1, speaker_id="Unknown")
    assert AzureStreamingProvider.to_event("interim", unknown, 0).speaker_label is None  # type: ignore[union-attr]
    assert AzureStreamingProvider.to_event("interim", SimpleNamespace(text=" "), 0) is None


def test_deepgram_stream_result_parsing_with_session_offset() -> None:
    message = {
        "type": "Results",
        "is_final": True,
        "start": 1.0,
        "duration": 1.5,
        "channel": {
            "alternatives": [
                {
                    "transcript": "la 27",
                    "confidence": 0.9,
                    "words": [{"speaker": 1}, {"speaker": 1}, {"speaker": 0}],
                }
            ]
        },
    }
    event = DeepgramStreamingProvider.parse_result(message, 0, offset_ms=10_000)
    assert event is not None
    assert (event.kind, event.audio_end_ms, event.speaker_label) == ("final", 12_500, "1")
    assert DeepgramStreamingProvider.parse_result({"type": "Metadata"}, 0) is None


def test_deepgram_stream_reconnects_and_resends_unconfirmed_audio() -> None:
    """Le serveur coupe la 1re connexion après 2 segments sans résultat final :
    la 2e connexion doit recevoir à nouveau tout l'audio depuis le début."""

    received: list[int] = []  # octets reçus par connexion

    async def fake_deepgram(ws: Any) -> None:
        connection = len(received)
        received.append(0)
        async for message in ws:
            if isinstance(message, bytes):
                received[connection] += len(message)
                seconds = received[connection] / 32_000
                await ws.send(
                    json.dumps(
                        {
                            "type": "Results",
                            "is_final": False,
                            "start": 0,
                            "duration": seconds,
                            "channel": {"alternatives": [{"transcript": "texte", "words": []}]},
                        }
                    )
                )
                if connection == 0 and received[0] >= 2 * 64_000:
                    await ws.close(code=1011)
                    return
            elif json.loads(message)["type"] == "CloseStream":
                seconds = received[connection] / 32_000
                await ws.send(
                    json.dumps(
                        {
                            "type": "Results",
                            "is_final": True,
                            "start": 0,
                            "duration": seconds,
                            "channel": {
                                "alternatives": [{"transcript": "texte final", "words": []}]
                            },
                        }
                    )
                )
                await ws.close()
                return

    async def source() -> AsyncIterator[AudioChunk]:
        for chunk in chunks():
            yield chunk
            await asyncio.sleep(0.01)

    async def scenario() -> list[Any]:
        async with websockets.serve(fake_deepgram, "127.0.0.1", 0) as server:
            port = next(iter(server.sockets)).getsockname()[1]
            provider = DeepgramStreamingProvider("k", base_url=f"ws://127.0.0.1:{port}")
            return [event async for event in provider.stream(source(), "fr-FR", [])]

    events = asyncio.run(scenario())
    kinds = [event.kind for event in events]
    assert "reconnected" in kinds
    assert kinds[-1] == "final"
    assert received[1] == len(PCM), "tout l'audio non confirmé est renvoyé"
    assert events[-1].audio_end_ms == 5000


def test_deepgram_stream_gives_up_explicitly() -> None:
    async def always_close(ws: Any) -> None:
        await ws.close(code=1011)

    async def source() -> AsyncIterator[AudioChunk]:
        for chunk in chunks():
            yield chunk
            await asyncio.sleep(0.01)

    async def scenario() -> None:
        async with websockets.serve(always_close, "127.0.0.1", 0) as server:
            port = next(iter(server.sockets)).getsockname()[1]
            provider = DeepgramStreamingProvider(
                "k", base_url=f"ws://127.0.0.1:{port}", max_reconnects=2
            )
            async for _event in provider.stream(source(), "fr-FR", []):
                pass

    with pytest.raises(TranscriptionUnavailable):
        asyncio.run(scenario())


def test_transient_deepgram_failure_is_retried_then_succeeds() -> None:
    """Une coupure de quelques secondes ne doit pas coûter la consultation."""
    calls = {"n": 0}

    def flaky(_request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            raise httpx.ConnectError("down")
        if calls["n"] == 2:
            return httpx.Response(429, json={})
        return httpx.Response(200, json=DEEPGRAM_RESPONSE)

    client = httpx.AsyncClient(transport=httpx.MockTransport(flaky))
    provider = DeepgramPrerecordedProvider("k", client=client, retry_backoff_s=(0.0, 0.0))
    result = asyncio.run(provider.transcribe(chunks(), "fr-FR", []))
    assert calls["n"] == 3
    assert result.segments
