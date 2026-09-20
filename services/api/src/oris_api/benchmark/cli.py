"""Ligne de commande du banc d'essai STT.

generate : fabrique le jeu synthétique (corpus lu par les voix françaises de macOS)
run      : transcrit le jeu avec les fournisseurs choisis et écrit le rapport
"""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

from oris_api.benchmark.dataset import Dataset
from oris_api.benchmark.runner import ProviderUnderTest, run_benchmark, write_outputs
from oris_api.config import Settings
from oris_api.domain.resolver import GAP_MARKER
from oris_api.synthetic.corpus import default_corpus

REPO = Path(__file__).resolve().parents[5]
DEFAULT_DATASET = REPO / "benchmarks" / "datasets" / "oris-synthetic-tts-v1"
VOICES = {
    "practitioner": "Thomas",
    "patient": "Aurélie (Enhanced)",
    "assistant": "Jacques",
    "companion": "Flo (Français (France))",
    "unknown": "Thomas",
}
PAUSE_MS = 400
GAP_SILENCE_MS = 2000


def synthesize(text: str, voice: str, output: Path, attempts: int = 3) -> None:
    """Voix macOS. `say` se bloque parfois sans raison : délai maximal et nouvel essai."""
    command = ["/usr/bin/say", "-v", voice, "-o", str(output), "--file-format=WAVE",
               "--data-format=LEI16@16000", text]  # fmt: skip
    for attempt in range(attempts):
        try:
            # Arguments fixes, texte du corpus synthétique.
            subprocess.run(command, check=True, capture_output=True, timeout=30)  # noqa: S603
            return
        except subprocess.TimeoutExpired:
            if attempt == attempts - 1:
                raise


def generate(out: Path, limit: int | None) -> Path:
    audio_dir = out / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    silence = b"\x00\x00" * (16 * PAUSE_MS)
    items = []
    cases = default_corpus().cases()[:limit] if limit else default_corpus().cases()
    with tempfile.TemporaryDirectory() as tmp:
        for case in cases:
            pcm = bytearray()
            references = []
            for segment in case.segments:
                if GAP_MARKER.match(segment.text):
                    pcm += b"\x00\x00" * (16 * GAP_SILENCE_MS)  # silence : rien à transcrire
                    continue
                part = Path(tmp) / f"{case.case_id}-{segment.segment_id}.wav"
                synthesize(segment.text, VOICES[segment.speaker_role], part)
                with wave.open(str(part), "rb") as source:
                    frames = source.readframes(source.getnframes())
                start = len(pcm) // 32
                pcm += frames
                references.append(
                    {
                        "role": segment.speaker_role,
                        "start_ms": start,
                        "end_ms": len(pcm) // 32,
                        "text": segment.text,
                    }
                )
                pcm += silence
            audio_file = f"audio/{case.case_id}.wav"
            with wave.open(str(out / audio_file), "wb") as target:
                target.setnchannels(1)
                target.setsampwidth(2)
                target.setframerate(16_000)
                target.writeframes(bytes(pcm))
            items.append(
                {
                    "audio_id": case.case_id,
                    "audio_file": audio_file,
                    "source_case_id": case.case_id,
                    "duration_ms": len(pcm) // 32,
                    "reference_segments": references,
                }
            )
            print(f"{case.case_id} ({len(pcm) // 32 / 1000:.1f} s)")
    manifest = {
        "name": out.name,
        "version": "1",
        "locale": "fr-FR",
        "synthetic_only": True,
        "consent_documented": False,
        "created_with": "macOS say, 16 kHz mono PCM",
        "voices": VOICES,
        "items": items,
    }
    path = out / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    return path


def providers(
    keys: list[str], settings: Settings, config: dict[str, dict[str, object]]
) -> list[ProviderUnderTest]:
    from oris_api.stt.azure_speech import AzureFastTranscriptionProvider, AzureStreamingProvider
    from oris_api.stt.deepgram import DeepgramPrerecordedProvider, DeepgramStreamingProvider

    if not settings.allow_external_stt:
        sys.exit(
            "ALLOW_EXTERNAL_STT=true requis dans services/api/.env "
            "(envoi d'audio à un fournisseur)."
        )
    chosen = []
    for key in keys:
        meta = config.get(key, {})
        rate = meta.get("usd_per_minute")
        common = {
            "usd_per_minute": float(rate) if isinstance(rate, int | float) else None,
            "compliance_gate": str(meta.get("compliance_gate", "not_reviewed")),
        }
        if key == "deepgram":
            if settings.deepgram_api_key is None:
                sys.exit("DEEPGRAM_API_KEY manquante dans services/api/.env")
            secret = settings.deepgram_api_key.get_secret_value()
            base = settings.deepgram_base_url
            chosen.append(
                ProviderUnderTest(
                    key,
                    DeepgramPrerecordedProvider(secret, base),
                    DeepgramPrerecordedProvider(secret, base, use_glossary=False),
                    DeepgramStreamingProvider(secret, base.replace("https://", "wss://")),
                    **common,  # type: ignore[arg-type]
                )
            )
        elif key == "azure_speech":
            if settings.azure_speech_key is None or not settings.azure_speech_endpoint:
                sys.exit(
                    "AZURE_SPEECH_KEY et AZURE_SPEECH_ENDPOINT requises dans services/api/.env"
                )
            secret = settings.azure_speech_key.get_secret_value()
            endpoint = settings.azure_speech_endpoint
            chosen.append(
                ProviderUnderTest(
                    key,
                    AzureFastTranscriptionProvider(secret, endpoint),
                    AzureFastTranscriptionProvider(secret, endpoint, use_glossary=False),
                    AzureStreamingProvider(secret, endpoint),
                    **common,  # type: ignore[arg-type]
                )
            )
        else:
            sys.exit(f"Fournisseur inconnu : {key} (deepgram, azure_speech)")
    return chosen


def run_extraction(args: argparse.Namespace) -> int:
    from oris_api.benchmark.extraction import ModelReport, run_model, summarize, write_outputs
    from oris_api.benchmark.record import record
    from oris_api.llm.anthropic_extraction import AnthropicExtractionProvider

    settings = Settings(_env_file=REPO / "services" / "api" / ".env")
    if not settings.allow_external_llm:
        sys.exit(
            "ALLOW_EXTERNAL_LLM=true requis dans services/api/.env "
            "(envoi du transcript à un modèle extérieur)."
        )
    if settings.anthropic_api_key is None:
        sys.exit("ANTHROPIC_API_KEY manquante dans services/api/.env")
    config = json.loads(args.config.read_text()) if args.config.exists() else {}
    cases = default_corpus().cases()
    if args.limit and args.limit < len(cases):
        # Échantillon réparti : esthétique, usures, composite, facettes, extraction, pièges.
        step = len(cases) // args.limit
        cases = cases[::step][: args.limit]
    reports = []
    for model in args.models.split(","):
        provider = AnthropicExtractionProvider(settings.anthropic_api_key.get_secret_value(), model)
        prices = config.get(model, {})
        report = ModelReport(
            key=model,
            version=provider.info.version,
            scores=asyncio.run(run_model(provider, cases)),
            usd_per_million_input=prices.get("usd_per_million_input"),
            usd_per_million_output=prices.get("usd_per_million_output"),
        )
        summarize(report)
        reports.append(report)
        print(f"{model} : {report.summary['fact_recall']} de rappel")
    print(f"Rapport : {write_outputs(reports, len(cases), args.out)}")
    for report in reports:
        record(
            component="clinical_extraction",
            candidate_version=report.version,
            dataset_name="oris-synthetic-consultations",
            dataset_version="100",
            item_count=len(cases),
            metrics={
                key: value
                for key, value in report.summary.items()
                if isinstance(value, int | float)
            },
            critical_regressions=report.critical_regressions,
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    gen = commands.add_parser("generate")
    gen.add_argument("--out", type=Path, default=DEFAULT_DATASET)
    gen.add_argument("--limit", type=int)
    check = commands.add_parser("check", help="contrôle hors ligne avec la référence (aucun envoi)")
    check.add_argument("--dataset", type=Path, default=DEFAULT_DATASET / "manifest.json")
    check.add_argument("--out", type=Path, default=REPO / "benchmarks" / "reports")
    extraction = commands.add_parser(
        "extraction", help="banc d'essai de l'extraction clinique (transcripts, sans audio)"
    )
    extraction.add_argument("--models", default="claude-sonnet-5")
    extraction.add_argument(
        "--limit", type=int, help="échantillon réparti sur les six familles du corpus"
    )
    extraction.add_argument("--config", type=Path, default=REPO / "benchmarks" / "providers.json")
    extraction.add_argument("--out", type=Path, default=REPO / "benchmarks" / "reports")
    run = commands.add_parser("run")
    run.add_argument("--dataset", type=Path, default=DEFAULT_DATASET / "manifest.json")
    run.add_argument("--providers", default="deepgram,azure_speech")
    run.add_argument(
        "--streaming", action="store_true", help="mesure aussi le direct (au rythme réel)"
    )
    run.add_argument("--speed", type=float, default=1.0)
    run.add_argument("--limit", type=int)
    run.add_argument("--config", type=Path, default=REPO / "benchmarks" / "providers.json")
    run.add_argument("--out", type=Path, default=REPO / "benchmarks" / "reports")
    args = parser.parse_args(argv)

    if args.command == "generate":
        print(f"Jeu écrit : {generate(args.out, args.limit)}")
        return 0

    if args.command == "extraction":
        return run_extraction(args)

    dataset = Dataset.load(args.dataset)
    if args.command == "check":
        from oris_api.benchmark.reference import ReferenceProvider

        candidate = ProviderUnderTest("reference", ReferenceProvider(dataset))
        [report] = asyncio.run(run_benchmark(dataset, [candidate]))
        for key in ("wer", "tooth_number_accuracy", "negation_preservation", "speaker_accuracy"):
            print(f"{key} = {report.summary[key]}")
        print(f"Rapport : {write_outputs([report], dataset, args.out / 'checks')}")
        return 0 if not report.critical_regressions else 1
    if args.limit:
        dataset = Dataset(dataset.name, dataset.version, dataset.locale, dataset.synthetic_only,
                          dataset.consent_documented, dataset.items[: args.limit])  # fmt: skip
    config = json.loads(args.config.read_text()) if args.config.exists() else {}
    settings = Settings(_env_file=REPO / "services" / "api" / ".env")
    candidates = providers(args.providers.split(","), settings, config)
    reports = asyncio.run(
        run_benchmark(dataset, candidates, streaming=args.streaming, speed=args.speed)
    )
    print(f"Rapport : {write_outputs(reports, dataset, args.out)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
