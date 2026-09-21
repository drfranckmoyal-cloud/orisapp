"""Le serveur local ouvert au Wi-Fi du cabinet n'ouvre pas les dossiers.

En local, l'identité de démonstration ne sert qu'aux appels venus de ce Mac. Un autre
appareil (l'iPhone du praticien) doit présenter un jeton.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def local_env(api: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    from oris_api.config import get_settings

    monkeypatch.setattr(get_settings(), "app_env", "local")


def client_depuis(hote: str) -> TestClient:
    from oris_api.main import app

    return TestClient(app, client=(hote, 51000))


def test_this_mac_needs_no_token(local_env: None) -> None:
    assert client_depuis("127.0.0.1").get("/patients").status_code == 200


def test_another_device_on_the_network_needs_a_token(local_env: None) -> None:
    refus = client_depuis("192.168.1.42").get("/patients")
    assert refus.status_code == 403
    assert refus.json()["code"] == "AUTHENTICATION_REQUIRED"
