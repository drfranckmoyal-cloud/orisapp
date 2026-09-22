"""Conversion du PCM capté (16 kHz mono 16 bits) en fichier WAV pour les fournisseurs."""

from __future__ import annotations

import io
import wave
from collections.abc import Iterable

from oris_api.domain.types import AudioChunk

SAMPLE_RATE = 16_000


def concatenate(chunks: Iterable[AudioChunk]) -> bytes:
    return b"".join(chunk.payload for chunk in sorted(chunks, key=lambda c: c.sequence))


def niveau(pcm: bytes) -> dict[str, float]:
    """Volume d'un enregistrement PCM 16 bits : crête et moyenne, de 0 à 1.

    Un simple nombre, jamais le son : il dit si le micro a capté quelque chose.
    """
    import array

    echantillons = array.array("h")
    echantillons.frombytes(pcm[: len(pcm) - len(pcm) % 2])
    if not echantillons:
        return {"crete": 0.0, "moyen": 0.0}
    crete = max(abs(x) for x in echantillons) / 32768
    moyen = (sum(x * x for x in echantillons) / len(echantillons)) ** 0.5 / 32768
    return {"crete": round(crete, 4), "moyen": round(moyen, 5)}


def est_une_note(volume: dict[str, float]) -> bool:
    """Un son au volume presque constant : une note pure (le son de test de l'app), pas
    une voix. Une voix alterne pics et silences : sa moyenne reste loin de sa crête
    (rapport < 0,35), un bruit uniforme est à 0,58, une sinusoïde à 0,71. On tranche à
    0,65 : seule la note est visée."""
    return volume["crete"] > 0 and volume["moyen"] / volume["crete"] > 0.65


#: En dessous, l'enregistrement est muet : le micro n'a rien capté (≈ -50 dBFS de crête).
SEUIL_SILENCE = 0.003


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
