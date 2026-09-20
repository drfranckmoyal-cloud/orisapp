#!/usr/bin/env python3
"""Vérifie un jeu d'enregistrements avant de l'utiliser (M11).

Sert surtout aux **séances jouées par des praticiens** : format du son, consentement
déclaré, référence exploitable. Un jeu qui ne passe pas ce contrôle ne doit pas entrer
dans le banc d'essai.

    services/api/.venv/bin/python scripts/check_dataset.py benchmarks/datasets/<nom>
"""

from __future__ import annotations

import argparse
import json
import sys
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXPECTED = (16_000, 1, 2)  # 16 kHz, mono, 16 bits
REQUIRED_ITEM_FIELDS = ("audio_id", "audio_file", "reference_segments")


def check(path: Path) -> list[str]:
    """Renvoie la liste des problèmes. Vide = le jeu est utilisable."""
    problems: list[str] = []
    manifest_path = path / "manifest.json"
    if not manifest_path.is_file():
        return [f"{path}/manifest.json est absent"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    if not manifest.get("name"):
        problems.append("le manifeste n'a pas de nom")
    if not manifest.get("locale"):
        problems.append("le manifeste ne dit pas la langue")
    synthetic = bool(manifest.get("synthetic_only"))
    consent = bool(manifest.get("consent_documented"))
    if not synthetic and not consent:
        problems.append(
            "jeu non synthétique sans consentement documenté : "
            "ajoutez consent_documented et la référence du document signé"
        )
    if not synthetic and not manifest.get("consent_reference"):
        problems.append("consent_reference manquant (où est écrit le consentement ?)")

    items = manifest.get("items") or []
    if not items:
        problems.append("aucun enregistrement dans le manifeste")

    for index, item in enumerate(items):
        missing = [field for field in REQUIRED_ITEM_FIELDS if not item.get(field)]
        if missing:
            problems.append(f"enregistrement {index + 1} : champs manquants {missing}")
            continue
        audio = path / str(item["audio_file"])
        if not audio.is_file():
            problems.append(f"{item['audio_id']} : fichier absent ({item['audio_file']})")
            continue
        try:
            with wave.open(str(audio), "rb") as handle:
                shape = (handle.getframerate(), handle.getnchannels(), handle.getsampwidth())
        except wave.Error as error:
            problems.append(f"{item['audio_id']} : fichier illisible ({error})")
            continue
        if shape != EXPECTED:
            problems.append(
                f"{item['audio_id']} : attendu 16 kHz mono 16 bits, trouvé "
                f"{shape[0]} Hz / {shape[1]} canal(aux) / {shape[2] * 8} bits"
            )
        roles = {segment.get("role") for segment in item["reference_segments"]}
        if not roles or roles == {None}:
            problems.append(f"{item['audio_id']} : la référence ne dit pas qui parle")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", help="dossier du jeu d'enregistrements")
    args = parser.parse_args()
    path = Path(args.dataset)
    if not path.is_absolute():
        path = ROOT / path

    problems = check(path)
    if not problems:
        print(f"{path.name} : utilisable.")
        return 0
    print(f"{path.name} : {len(problems)} problème(s)\n", file=sys.stderr)
    for problem in problems:
        print(f"  - {problem}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
