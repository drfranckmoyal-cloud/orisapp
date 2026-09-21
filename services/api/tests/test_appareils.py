"""Appareils connectés : les voir, en autoriser un depuis le Mac, en déconnecter un."""

from __future__ import annotations

from typing import Any


def test_a_device_is_authorised_listed_then_disconnected(api: Any) -> None:
    cree = api.post("/me/appareils", json={"nom": "iPhone d'essai"})
    assert cree.status_code == 201
    corps = cree.json()
    assert corps["code"].startswith("oris_") and corps["actif"] is True
    liste = api.get("/me/appareils").json()
    assert [a["nom"] for a in liste] == ["iPhone d'essai"]
    assert "code" not in liste[0]
    assert api.delete(f"/me/appareils/{corps['id']}").status_code == 204
    assert api.get("/me/appareils").json()[0]["actif"] is False
    # Le code déconnecté n'ouvre plus rien.
    refus = api.get("/patients", headers={"Authorization": f"Bearer {corps['code']}"})
    assert refus.status_code == 403
