#!/usr/bin/env python3
"""Prépare des consultations jouées pour le banc d'essai (M11).

Convertit les enregistrements reçus en 16 kHz mono 16 bits, lit les transcriptions de
référence (« praticien | … »), et écrit le manifeste du jeu de données.

**Refuse d'écrire un jeu non synthétique sans consentement documenté et référencé** :
c'est la même règle que `scripts/check_dataset.py` et que la porte d'entrée en bêta.

    services/api/.venv/bin/python scripts/prepare_recordings.py \\
        --source ~/Desktop/seance-2026-09-27 \\
        --name cabinet-2026-09 \\
        --consent "consentements/2026-09-27-seance-03.pdf"
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import wave
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATASETS = ROOT / "benchmarks/datasets"
AUDIO_SUFFIXES = (".wav", ".m4a", ".mp3", ".aac", ".caf", ".aiff", ".mp4")
ROLES = {
    "praticien": "practitioner",
    "patient": "patient",
    "assistant": "assistant",
    "assistante": "assistant",
    "accompagnant": "companion",
}
SAMPLE_RATE = 16_000


@dataclass(frozen=True)
class Recording:
    audio_id: str
    source: Path
    transcript: Path | None


def converter(source: Path, target: Path) -> list[str]:
    """Commande de conversion : afconvert (macOS) ou ffmpeg."""
    if shutil.which("afconvert"):
        return [
            "afconvert", str(source), str(target),
            "-f", "WAVE", "-d", f"LEI16@{SAMPLE_RATE}", "-c", "1",
        ]  # fmt: skip
    if shutil.which("ffmpeg"):
        return [
            "ffmpeg", "-y", "-i", str(source),
            "-ac", "1", "-ar", str(SAMPLE_RATE), "-sample_fmt", "s16", str(target),
        ]  # fmt: skip
    raise RuntimeError("Ni afconvert ni ffmpeg : impossible de convertir le son.")


def convert(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(  # noqa: S603 - commande construite ici, chemins contrôlés
        converter(source, target), capture_output=True, text=True
    )
    if result.returncode != 0 or not target.is_file():
        raise RuntimeError(f"Conversion échouée pour {source.name} : {result.stderr[:300]}")


def read_reference(path: Path) -> list[dict[str, str]]:
    """« praticien | phrase » -> segments de référence, rôle traduit."""
    segments: list[dict[str, str]] = []
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "|" not in line:
            raise ValueError(f"{path.name} ligne {number} : format attendu « rôle | texte »")
        spoken, text = (part.strip() for part in line.split("|", 1))
        role = ROLES.get(spoken.lower())
        if role is None:
            raise ValueError(f"{path.name} ligne {number} : rôle inconnu « {spoken} »")
        if text:
            segments.append({"role": role, "text": text})
    return segments


def duration_ms(path: Path) -> int:
    with wave.open(str(path), "rb") as handle:
        return round(handle.getnframes() / handle.getframerate() * 1000)


def collect(source: Path) -> list[Recording]:
    found: list[Recording] = []
    for audio in sorted(source.iterdir()):
        if audio.suffix.lower() not in AUDIO_SUFFIXES:
            continue
        transcript = audio.with_suffix(".txt")
        found.append(
            Recording(
                audio_id=audio.stem,
                source=audio,
                transcript=transcript if transcript.is_file() else None,
            )
        )
    return found


def build(source: Path, name: str, consent: str, locale: str = "fr-FR") -> Path:
    if not consent.strip():
        raise ValueError(
            "Consentement manquant : indiquez où sont rangés les documents signés "
            "(--consent). Sans cela, ce jeu ne doit pas exister."
        )
    recordings = collect(source)
    if not recordings:
        raise ValueError(f"Aucun enregistrement dans {source}")

    target = DATASETS / name
    items = []
    for recording in recordings:
        wav = target / "audio" / f"{recording.audio_id}.wav"
        convert(recording.source, wav)
        if recording.transcript is None:
            print(f"  ! {recording.audio_id} : transcription de référence absente")
            segments: list[dict[str, str]] = []
        else:
            segments = read_reference(recording.transcript)
        items.append(
            {
                "audio_id": recording.audio_id,
                "audio_file": f"audio/{recording.audio_id}.wav",
                "duration_ms": duration_ms(wav),
                "reference_segments": segments,
            }
        )

    manifest = {
        "name": name,
        "version": "1",
        "locale": locale,
        "synthetic_only": False,
        "consent_documented": True,
        "consent_reference": consent,
        "created_with": "consultations jouées par des praticiens",
        "items": items,
    }
    (target / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, help="dossier des enregistrements reçus")
    parser.add_argument("--name", required=True, help="nom du jeu de données")
    parser.add_argument("--consent", required=True, help="où sont rangés les consentements signés")
    parser.add_argument("--locale", default="fr-FR")
    args = parser.parse_args()

    try:
        target = build(Path(args.source).expanduser(), args.name, args.consent, args.locale)
    except (ValueError, RuntimeError) as error:
        print(f"Refusé : {error}", file=sys.stderr)
        return 1
    print(f"\n{target.relative_to(ROOT)} écrit.")
    print(
        "Contrôlez-le : services/api/.venv/bin/python scripts/check_dataset.py "
        f"benchmarks/datasets/{args.name}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
