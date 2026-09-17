"""Stockage transitoire des segments audio (D010 : audio éphémère).

Aucun segment n'est conservé après la fin du traitement. `local_temp` écrit hors
du dépôt et hors du Bureau iCloud ; l'environnement de production (stockage objet
HDS chiffré) sera un autre adaptateur.
"""

from __future__ import annotations

import shutil
import threading
from pathlib import Path
from typing import Protocol
from uuid import UUID

from oris_api.config import Settings


class AudioSink(Protocol):
    def store(self, session_id: UUID, sequence: int, payload: bytes) -> None: ...

    def load(self, session_id: UUID, sequence: int) -> bytes | None: ...

    def purge(self, session_id: UUID) -> None: ...

    def count(self, session_id: UUID) -> int: ...


class MemoryAudioSink:
    def __init__(self) -> None:
        self._data: dict[UUID, dict[int, bytes]] = {}
        self._lock = threading.Lock()

    def store(self, session_id: UUID, sequence: int, payload: bytes) -> None:
        with self._lock:
            self._data.setdefault(session_id, {})[sequence] = payload

    def load(self, session_id: UUID, sequence: int) -> bytes | None:
        with self._lock:
            return self._data.get(session_id, {}).get(sequence)

    def purge(self, session_id: UUID) -> None:
        with self._lock:
            self._data.pop(session_id, None)

    def count(self, session_id: UUID) -> int:
        with self._lock:
            return len(self._data.get(session_id, {}))


class LocalTempAudioSink:
    def __init__(self, root: Path) -> None:
        self._root = root

    def _dir(self, session_id: UUID) -> Path:
        return self._root / str(session_id)

    def store(self, session_id: UUID, sequence: int, payload: bytes) -> None:
        directory = self._dir(session_id)
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        temporary = directory / f"{sequence:08d}.part"
        temporary.write_bytes(payload)
        temporary.replace(directory / f"{sequence:08d}.pcm")

    def load(self, session_id: UUID, sequence: int) -> bytes | None:
        path = self._dir(session_id) / f"{sequence:08d}.pcm"
        return path.read_bytes() if path.exists() else None

    def purge(self, session_id: UUID) -> None:
        shutil.rmtree(self._dir(session_id), ignore_errors=True)

    def count(self, session_id: UUID) -> int:
        directory = self._dir(session_id)
        return len(list(directory.glob("*.pcm"))) if directory.exists() else 0


def build_sink(settings: Settings) -> AudioSink:
    if settings.audio_sink == "memory":
        return MemoryAudioSink()
    return LocalTempAudioSink(settings.audio_temp_dir)
