"""Envoi par l'API de Gmail : le web ordinaire, quand l'hébergeur bloque les ports de courriel."""

# ruff: noqa: S105, S106 - faux jetons d'essai

from __future__ import annotations

import base64
import json
import urllib.parse
from uuid import uuid4

import pytest

from oris_api.config import Settings
from oris_api.services.courriel import (
    ENVOI_GMAIL,
    JETON_GOOGLE,
    EnvoiImpossible,
    GmailMessagerie,
    SmtpMessagerie,
    construire,
    messagerie_de,
)


def _message():
    return construire(
        "praticien@example.org",
        "Dr Essai",
        "confrere@example.org",
        "Compte rendu",
        "Bonjour,",
        b"%PDF-1.4 essai",
        "cr.pdf",
        uuid4(),
    )


class Google:
    """Un faux Google : répond au jeton puis à l'envoi, et garde ce qu'il a reçu."""

    def __init__(self, jeton: int = 200, envoi: int = 200) -> None:
        self.codes = {JETON_GOOGLE: jeton, ENVOI_GMAIL: envoi}
        self.recu: list[tuple[str, bytes, dict[str, str]]] = []

    def __call__(self, adresse: str, donnees: bytes, entetes: dict[str, str]):
        self.recu.append((adresse, donnees, entetes))
        corps = json.dumps({"access_token": "jeton-du-moment"}).encode()
        return self.codes[adresse], corps


def test_envoie_le_message_entier_avec_le_jeton_du_moment() -> None:
    google = Google()
    GmailMessagerie("client", "secret", "durable", poster=google).envoyer(_message())

    (a1, d1, _), (a2, d2, e2) = google.recu
    assert a1 == JETON_GOOGLE
    champs = dict(urllib.parse.parse_qsl(d1.decode()))
    assert champs["refresh_token"] == "durable"
    assert champs["grant_type"] == "refresh_token"
    assert a2 == ENVOI_GMAIL
    assert e2["Authorization"] == "Bearer jeton-du-moment"
    brut = base64.urlsafe_b64decode(json.loads(d2)["raw"])
    assert b"To: confrere@example.org" in brut
    assert b"cr.pdf" in brut  # la pièce jointe part avec


@pytest.mark.parametrize(
    ("jeton", "envoi", "code"),
    [
        (400, 200, "GMAIL_AUTH_FAILED"),  # accès retiré dans le compte Google
        (200, 403, "GMAIL_AUTH_FAILED"),
        (200, 400, "SMTP_RECIPIENT_REFUSED"),
        (503, 200, "SMTP_UNAVAILABLE"),
        (200, 500, "SMTP_UNAVAILABLE"),
    ],
)
def test_chaque_refus_se_dit(jeton: int, envoi: int, code: str) -> None:
    with pytest.raises(EnvoiImpossible) as refus:
        GmailMessagerie("c", "s", "d", poster=Google(jeton, envoi)).envoyer(_message())
    assert refus.value.code == code


def test_reseau_coupe() -> None:
    def coupe(*_: object):
        raise OSError("réseau")

    with pytest.raises(EnvoiImpossible) as refus:
        GmailMessagerie("c", "s", "d", poster=coupe).envoyer(_message())
    assert refus.value.code == "SMTP_UNAVAILABLE"


def test_gmail_passe_avant_smtp_quand_il_est_pose() -> None:
    base = {"smtp_user": "praticien@example.org", "smtp_password": "mdp"}
    assert isinstance(messagerie_de(Settings(**base)), SmtpMessagerie)
    avec = Settings(
        **base,
        gmail_client_id="client",
        gmail_client_secret="secret",
        gmail_refresh_token="durable",
    )
    assert isinstance(messagerie_de(avec), GmailMessagerie)
    # Vide dans .env = absent : on reste sur SMTP.
    vide = Settings(**base, gmail_client_id="client", gmail_refresh_token="  ")
    assert isinstance(messagerie_de(vide), SmtpMessagerie)
