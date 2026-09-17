#!/usr/bin/env python3
"""Exporte le contrat OpenAPI de l'API dans packages/openapi/openapi.json.

Les clients (types TypeScript du web) sont générés depuis ce fichier.
À lancer avec l'environnement Python de services/api :
  services/api/.venv/bin/python scripts/export_openapi.py [--check]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from oris_api.main import app

OUT = Path(__file__).resolve().parent.parent / "packages" / "openapi" / "openapi.json"


def main() -> int:
    content = json.dumps(app.openapi(), indent=2, ensure_ascii=False) + "\n"
    if "--check" in sys.argv:
        if not OUT.exists() or OUT.read_text() != content:
            print("packages/openapi/openapi.json périmé — lancer scripts/export_openapi.py")
            return 1
        return 0
    OUT.write_text(content)
    print(f"écrit {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
