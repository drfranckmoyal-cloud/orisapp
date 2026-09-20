#!/usr/bin/env python3
"""Porte d'entrée en bêta : la règle de sortie, exécutable (IMPLEMENTATION_PLAN M11).

Rien n'est coché à la main. Chaque point est vérifié dans le dépôt, et la sortie dit
**pourquoi** elle refuse. Un point qui dépend d'un contrat ou d'un hébergeur est déclaré
comme tel : il ne se coche pas en écrivant du code.

    services/api/.venv/bin/python scripts/beta_gate.py
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROVIDERS = ROOT / "benchmarks/providers.json"
DATASETS = ROOT / "benchmarks/datasets"
VENDORS = ROOT / "docs/VENDORS.md"
EXTERNAL_PROVIDERS = ("deepgram", "azure_speech", "claude-sonnet-5")
TO_DOCUMENT = "à documenter"


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    detail: str
    blocking: bool = True


def providers_reviewed() -> Check:
    """Aucun fournisseur externe ne passe tant que sa conformité n'est pas revue."""
    data = json.loads(PROVIDERS.read_text(encoding="utf-8"))
    pending = [
        name for name in EXTERNAL_PROVIDERS if data.get(name, {}).get("compliance_gate") != "passed"
    ]
    return Check(
        "Conformité des fournisseurs revue",
        not pending,
        "revue faite" if not pending else f"non revus : {', '.join(pending)}",
    )


def vendor_flows_documented() -> Check:
    text = VENDORS.read_text(encoding="utf-8") if VENDORS.exists() else ""
    remaining = text.count(TO_DOCUMENT)
    return Check(
        "Flux de données fournisseurs documentés",
        VENDORS.exists() and remaining == 0,
        "complet" if remaining == 0 else f"{remaining} case(s) « à documenter »",
    )


def professional_sessions() -> Check:
    """Des consultations jouées par des praticiens, avec consentement écrit."""
    real = []
    for manifest_path in sorted(DATASETS.glob("*/manifest.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("synthetic_only"):
            continue
        if manifest.get("consent_documented"):
            real.append(f"{manifest.get('name')} ({len(manifest.get('items', []))} séances)")
    return Check(
        "Séances jouées par des praticiens, consentement documenté",
        bool(real),
        ", ".join(real) if real else "aucun jeu non synthétique avec consentement",
    )


def datasets_declare_their_nature() -> Check:
    """Un jeu de données sans consentement déclaré ne doit pas exister."""
    faulty = []
    for manifest_path in sorted(DATASETS.glob("*/manifest.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not manifest.get("synthetic_only") and not manifest.get("consent_documented"):
            faulty.append(str(manifest_path.relative_to(ROOT)))
    return Check(
        "Chaque jeu de données déclare son origine",
        not faulty,
        "conforme" if not faulty else f"sans consentement : {', '.join(faulty)}",
    )


def tests_pass() -> Check:
    result = subprocess.run(  # noqa: S603 - commande fixe, dans le dépôt
        [str(ROOT / "services/api/.venv/bin/pytest"), "-q"],
        cwd=ROOT / "services/api",
        capture_output=True,
        text=True,
    )
    last = [line for line in result.stdout.splitlines() if line.strip()]
    return Check(
        "Tests serveur au vert",
        result.returncode == 0,
        last[-1] if last else "pytest n'a rien dit",
    )


def hosting_ready() -> Check:
    """Hébergement agréé : une décision et un contrat, pas du code."""
    return Check(
        "Hébergement agréé données de santé en place",
        False,
        "hors du code : à contractualiser (HDS, chiffrement au repos, sauvegardes, MFA)",
    )


def main() -> int:
    checks = [
        tests_pass(),
        datasets_declare_their_nature(),
        professional_sessions(),
        providers_reviewed(),
        vendor_flows_documented(),
        hosting_ready(),
    ]
    width = max(len(check.name) for check in checks)
    print("Porte d'entrée en bêta — Oris\n")
    for check in checks:
        mark = "✔" if check.passed else "✘"
        print(f"  {mark}  {check.name.ljust(width)}   {check.detail}")

    blocking = [check for check in checks if not check.passed and check.blocking]
    print()
    if blocking:
        print(f"REFUSÉ — {len(blocking)} point(s) bloquant(s). Aucun patient réel.")
        return 1
    print("ACCORDÉ — les conditions de la bêta sont réunies.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
