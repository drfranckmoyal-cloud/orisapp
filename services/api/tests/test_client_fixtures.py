"""Réponses réelles de l'API figées pour les tests de contrat iOS (spec §100).

Les fichiers de apps/ios/OrisTests/Fixtures sont produits par ce test à partir
de vraies réponses (identifiants et dates normalisés). Si l'API change, ce test
échoue : relancer avec ORIS_UPDATE_FIXTURES=1, puis les tests iOS vérifient que
l'app décode toujours.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

from tests.conftest import REPO_ROOT, run_synthetic

FIXTURES = REPO_ROOT / "apps" / "ios" / "OrisTests" / "Fixtures"
UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?")


def normalize(payload: Any) -> str:
    text = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True)
    mapping: dict[str, str] = {}

    def stable_uuid(match: re.Match[str]) -> str:
        value = match.group(0)
        mapping.setdefault(value, f"00000000-0000-4000-8000-{len(mapping) + 1:012d}")
        return mapping[value]

    text = UUID.sub(stable_uuid, text)
    return TIMESTAMP.sub("2026-09-17T09:00:00+00:00", text) + "\n"


def test_ios_fixtures_match_live_api_responses(api: Any) -> None:
    encounter = run_synthetic(api, "ORIS-SYN-099")
    eid = encounter["id"]
    responses = {
        "encounters.json": api.get("/encounters").json(),
        "encounter.json": api.get(f"/encounters/{eid}").json(),
        "documents.json": api.get(f"/encounters/{eid}/documents").json(),
        "clinical_object.json": api.get(f"/encounters/{eid}/clinical-object").json(),
        "transcript.json": api.get(f"/encounters/{eid}/transcript").json(),
    }
    plan_case = run_synthetic(api, "ORIS-SYN-093")
    responses["documents_with_plan.json"] = api.get(
        f"/encounters/{plan_case['id']}/documents"
    ).json()
    responses["clinical_object_with_plan.json"] = api.get(
        f"/encounters/{plan_case['id']}/clinical-object"
    ).json()

    update = os.environ.get("ORIS_UPDATE_FIXTURES") == "1"
    stale = []
    for name, payload in responses.items():
        path = FIXTURES / name
        content = normalize(payload)
        if update:
            FIXTURES.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        elif not path.exists() or path.read_text() != content:
            stale.append(name)
    assert stale == [], f"Fixtures iOS périmées : {stale} (ORIS_UPDATE_FIXTURES=1 pytest ...)"
