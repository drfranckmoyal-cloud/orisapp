"""Préparation des consultations jouées : conversion, référence, consentement exigé."""

from __future__ import annotations

import importlib.util
import json
import shutil
import struct
import sys
import wave
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[3]

# La conversion du son passe par un outil du système (afconvert sur macOS, ffmpeg
# ailleurs). Sans lui, le test n'a rien à vérifier : on le saute au lieu d'échouer.
besoin_convertisseur = pytest.mark.skipif(
    shutil.which("afconvert") is None and shutil.which("ffmpeg") is None,
    reason="ni afconvert ni ffmpeg sur cette machine",
)


def load() -> Any:
    spec = importlib.util.spec_from_file_location(
        "prepare_recordings", ROOT / "scripts/prepare_recordings.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["prepare_recordings"] = module
    spec.loader.exec_module(module)
    return module


def session(tmp_path: Path, transcript: str | None = None) -> Path:
    source = tmp_path / "seance"
    source.mkdir()
    with wave.open(str(source / "SEANCE-2026-09-27-01.wav"), "wb") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(44_100)
        handle.writeframes(struct.pack("<hh", 0, 0) * 44_100)
    if transcript is not None:
        (source / "SEANCE-2026-09-27-01.txt").write_text(transcript, encoding="utf-8")
    return source


def test_a_reference_transcript_is_read_with_its_speakers(tmp_path: Path) -> None:
    module = load()
    path = tmp_path / "reference.txt"
    path.write_text(
        "# séance 1\npraticien | Sur la 16, sensibilité au froid.\n\n"
        "patient   | Je n'ai pas mal la nuit.\n",
        encoding="utf-8",
    )
    assert module.read_reference(path) == [
        {"role": "practitioner", "text": "Sur la 16, sensibilité au froid."},
        {"role": "patient", "text": "Je n'ai pas mal la nuit."},
    ]


def test_an_unknown_speaker_is_refused_instead_of_guessed(tmp_path: Path) -> None:
    module = load()
    path = tmp_path / "reference.txt"
    path.write_text("dentiste | Sur la 16.\n", encoding="utf-8")
    with pytest.raises(ValueError, match="rôle inconnu"):
        module.read_reference(path)


def test_a_line_without_a_speaker_is_refused(tmp_path: Path) -> None:
    module = load()
    path = tmp_path / "reference.txt"
    path.write_text("Sur la 16, sensibilité au froid.\n", encoding="utf-8")
    with pytest.raises(ValueError, match=r"format attendu"):
        module.read_reference(path)


def test_nothing_is_written_without_a_consent_reference(tmp_path: Path) -> None:
    module = load()
    with pytest.raises(ValueError, match="Consentement manquant"):
        module.build(session(tmp_path), "essai-sans-consentement", "  ")
    assert not (ROOT / "benchmarks/datasets/essai-sans-consentement").exists()


@besoin_convertisseur
def test_the_recordings_are_converted_and_the_manifest_is_written(tmp_path: Path) -> None:
    module = load()
    module.DATASETS = tmp_path / "datasets"
    source = session(tmp_path, "praticien | Sur la 16.\npatient | Pas la nuit.\n")

    target = module.build(source, "cabinet-essai", "consentements/2026-09-27.pdf")
    manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["synthetic_only"] is False
    assert manifest["consent_documented"] is True
    assert manifest["consent_reference"] == "consentements/2026-09-27.pdf"

    item = manifest["items"][0]
    assert item["reference_segments"][0]["role"] == "practitioner"
    with wave.open(str(target / item["audio_file"]), "rb") as handle:
        assert (handle.getframerate(), handle.getnchannels(), handle.getsampwidth()) == (
            16_000,
            1,
            2,
        )

    # Le jeu produit passe le contrôle qui garde le banc d'essai.
    check_spec = importlib.util.spec_from_file_location(
        "check_dataset", ROOT / "scripts/check_dataset.py"
    )
    assert check_spec is not None and check_spec.loader is not None
    check = importlib.util.module_from_spec(check_spec)
    sys.modules["check_dataset"] = check
    check_spec.loader.exec_module(check)
    assert check.check(target) == []
