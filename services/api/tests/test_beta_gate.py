"""Porte d'entrée en bêta et contrôle des jeux d'enregistrements (M11)."""

from __future__ import annotations

import importlib.util
import json
import struct
import sys
import wave
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]


def load(name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, ROOT / f"scripts/{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def write_wav(path: Path, sample_rate: int = 16_000, channels: int = 1) -> None:
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(channels)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(struct.pack("<h", 0) * 1600)


def dataset(tmp_path: Path, **manifest: Any) -> Path:
    folder = tmp_path / "jeu"
    (folder / "audio").mkdir(parents=True)
    write_wav(folder / "audio/S1.wav")
    base = {
        "name": "jeu",
        "locale": "fr-FR",
        "synthetic_only": False,
        "consent_documented": True,
        "consent_reference": "formulaire signé le 20/09/2026",
        "items": [
            {
                "audio_id": "S1",
                "audio_file": "audio/S1.wav",
                "reference_segments": [{"role": "practitioner", "text": "Sur la 16."}],
            }
        ],
    }
    (folder / "manifest.json").write_text(
        json.dumps({**base, **manifest}, ensure_ascii=False), encoding="utf-8"
    )
    return folder


def test_a_well_formed_professional_dataset_passes(tmp_path: Path) -> None:
    assert load("check_dataset").check(dataset(tmp_path)) == []


def test_a_recording_without_consent_is_refused(tmp_path: Path) -> None:
    problems = load("check_dataset").check(
        dataset(tmp_path, consent_documented=False, consent_reference=None)
    )
    assert any("consentement" in problem for problem in problems)


def test_a_recording_in_the_wrong_format_is_refused(tmp_path: Path) -> None:
    folder = dataset(tmp_path)
    write_wav(folder / "audio/S1.wav", sample_rate=44_100, channels=2)
    problems = load("check_dataset").check(folder)
    assert any("16 kHz mono" in problem for problem in problems)


def test_a_reference_without_speakers_is_refused(tmp_path: Path) -> None:
    folder = dataset(tmp_path)
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    manifest["items"][0]["reference_segments"] = [{"text": "Sur la 16."}]
    (folder / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    assert any("qui parle" in problem for problem in load("check_dataset").check(folder))


def test_the_beta_gate_refuses_while_the_vendors_are_not_reviewed() -> None:
    gate = load("beta_gate")
    assert gate.providers_reviewed().passed is False
    assert gate.vendor_flows_documented().passed is False
    # Un point qui dépend d'un contrat ne se coche pas en écrivant du code.
    hosting = gate.hosting_ready()
    assert hosting.passed is False and "hors du code" in hosting.detail


def test_the_beta_gate_sees_that_todays_dataset_is_synthetic_only() -> None:
    gate = load("beta_gate")
    assert gate.datasets_declare_their_nature().passed is True
    assert gate.professional_sessions().passed is False
