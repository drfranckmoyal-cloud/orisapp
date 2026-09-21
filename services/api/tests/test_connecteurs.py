"""Voyants Doctolib et SmileCloud, traduits de l'état de Dental Lens."""

from __future__ import annotations

from typing import Any

from oris_api.services.connecteurs import voyants

ACTIVE = {"extension": {"session": "ok"}, "extension_active": True, "smilecloud_ouvert": True}


def test_dental_lens_silent_means_unknown_not_broken() -> None:
    v = voyants(None)
    assert v["doctolib"]["etat"] == "inconnu" and v["doctolib"]["ouvrir"] is None


def test_doctolib_asking_for_login_offers_to_reconnect() -> None:
    v = voyants({**ACTIVE, "doctolib": {"etat": "connexion"}})
    assert v["doctolib"]["etat"] == "à reconnecter"
    assert v["doctolib"]["ton"] == "alerte" and v["doctolib"]["ouvrir"] == "doctolib"


def test_open_doctolib_and_confirmed_smilecloud_are_green() -> None:
    v = voyants(
        {
            **ACTIVE,
            "doctolib": {
                "etat": "ok",
                "derniere_lecture": {
                    "jour": "2026-09-22",
                    "lu_le": "2026-09-22T08:10:00",
                    "rendezvous": 9,
                },
            },
        }
    )
    assert v["doctolib"]["ton"] == "actif" and "9 rendez-vous" in v["doctolib"]["detail"]
    assert v["smilecloud"]["etat"] == "connecté"
    assert "pas encore" in v["smilecloud"]["detail"]


def test_closed_chrome_is_said_plainly() -> None:
    v = voyants({"extension": {}, "extension_active": False})
    assert v["doctolib"]["etat"] == "Chrome fermé" and v["doctolib"]["ouvrir"] == "doctolib"


def test_route_answers_even_without_dental_lens(api: Any, monkeypatch: Any) -> None:
    monkeypatch.setattr("oris_api.services.connecteurs.lire_etat_dental_lens", lambda: None)
    corps = api.get("/connecteurs").json()
    assert corps["doctolib"]["etat"] == "inconnu" and corps["peut_ouvrir"] is True
