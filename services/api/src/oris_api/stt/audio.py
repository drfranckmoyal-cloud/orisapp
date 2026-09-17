"""Conversion du PCM capté (16 kHz mono 16 bits) en fichier WAV pour les fournisseurs."""

from __future__ import annotations

import io
import wave
from collections.abc import Iterable

from oris_api.domain.types import AudioChunk

SAMPLE_RATE = 16_000


def concatenate(chunks: Iterable[AudioChunk]) -> bytes:
    return b"".join(chunk.payload for chunk in sorted(chunks, key=lambda c: c.sequence))


def pcm_to_wav(pcm: bytes, sample_rate: int = SAMPLE_RATE) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        output.writeframes(pcm)
    return buffer.getvalue()


def wav_to_pcm(data: bytes) -> tuple[bytes, int]:
    """PCM brut et fréquence d'un WAV mono 16 bits (refuse tout autre format)."""
    with wave.open(io.BytesIO(data), "rb") as source:
        if source.getnchannels() != 1 or source.getsampwidth() != 2:
            raise ValueError("WAV mono 16 bits attendu")
        return source.readframes(source.getnframes()), source.getframerate()


def split_pcm(pcm: bytes, session_id: str, chunk_ms: int = 2000) -> list[AudioChunk]:
    """Découpe en segments comme les clients (utile au banc d'essai temps réel)."""
    import hashlib

    size = chunk_ms * SAMPLE_RATE // 1000 * 2
    chunks = []
    for index, start in enumerate(range(0, len(pcm), size)):
        payload = pcm[start : start + size]
        chunks.append(
            AudioChunk(
                session_id=session_id,
                sequence=index,
                timestamp_ms=start // 32,
                checksum=hashlib.sha256(payload).hexdigest(),
                payload=payload,
            )
        )
    return chunks
