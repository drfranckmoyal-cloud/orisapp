"""L'extension Chrome parle au serveur en ligne avec le secret partagé.

Depuis le 11/11/2026, les dossiers vivent sur le serveur en ligne : l'extension (journée
Doctolib, dépôts SmileCloud) doit pouvoir l'appeler de l'extérieur. Le secret partagé
fait foi, d'où que vienne l'appel ; sans lui, rien n'est ouvert hors de la machine.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import SecretStr

from oris_api.api.dependencies import extension_autorisee
from oris_api.services.errors import Forbidden


def appel(hote: str) -> Any:
    return SimpleNamespace(client=SimpleNamespace(host=hote))


def reglages(secret: str | None) -> Any:
    return SimpleNamespace(journee_depot_token=SecretStr(secret) if secret else None)


def test_le_secret_ouvre_depuis_l_exterieur() -> None:
    extension_autorisee(appel("82.127.197.185"), reglages("s3cret"), "Bearer s3cret")


def test_un_mauvais_secret_est_refuse_meme_sur_le_mac() -> None:
    with pytest.raises(Forbidden) as refus:
        extension_autorisee(appel("127.0.0.1"), reglages("s3cret"), "Bearer autre")
    assert refus.value.code == "DEPOT_JETON_INVALIDE"


def test_sans_secret_rien_n_est_ouvert_hors_de_la_machine() -> None:
    with pytest.raises(Forbidden) as refus:
        extension_autorisee(appel("82.127.197.185"), reglages(None), None)
    assert refus.value.code == "DEPOT_NON_LOCAL"


def test_sur_le_mac_sans_secret_pose_tout_passe_comme_avant() -> None:
    extension_autorisee(appel("127.0.0.1"), reglages(None), None)


def test_un_secret_pose_s_exige_aussi_sur_le_mac() -> None:
    with pytest.raises(Forbidden) as refus:
        extension_autorisee(appel("127.0.0.1"), reglages("s3cret"), None)
    assert refus.value.code == "DEPOT_JETON_INVALIDE"
