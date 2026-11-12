"""Envoi des documents par courriel.

Oris envoie depuis la boîte du praticien (SMTP, par exemple Gmail avec un mot de passe
d'application rangé dans `.env`). Chaque destinataire reçoit **son propre** message :
aucun ne voit l'adresse des autres. Chaque envoi réussi est noté comme un envoi du
document (« Envoyé à … »), avec le canal courriel.

Le contenu part hors d'Oris : c'est un geste du praticien, jamais automatique, et le
journal d'audit n'en garde que des identifiants.
"""

from __future__ import annotations

import base64
import json
import smtplib
import ssl
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from email.message import EmailMessage
from typing import Protocol
from uuid import UUID

import certifi

from oris_api.config import Settings


class Messagerie(Protocol):
    def envoyer(self, message: EmailMessage) -> None: ...


class EnvoiImpossible(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass
class SmtpMessagerie:
    hote: str
    port: int
    utilisateur: str
    mot_de_passe: str
    delai_s: float = 30

    def envoyer(self, message: EmailMessage) -> None:
        # Liste de certificats fournie avec Oris : le Python de python.org n'utilise pas
        # celle du Mac, et la vérification du serveur ne doit jamais être désactivée.
        contexte = ssl.create_default_context(cafile=certifi.where())
        try:
            with smtplib.SMTP(self.hote, self.port, timeout=self.delai_s) as serveur:
                serveur.starttls(context=contexte)
                serveur.login(self.utilisateur, self.mot_de_passe)
                serveur.send_message(message)
        except smtplib.SMTPAuthenticationError as error:
            raise EnvoiImpossible("SMTP_AUTH_FAILED") from error
        except smtplib.SMTPRecipientsRefused as error:
            raise EnvoiImpossible("SMTP_RECIPIENT_REFUSED") from error
        except (smtplib.SMTPException, OSError) as error:
            raise EnvoiImpossible("SMTP_UNAVAILABLE") from error


#: Ce que Google appelle pour échanger le jeton durable contre un jeton du moment, puis
#: pour envoyer. Les deux passent par le web ordinaire (port 443), que l'hébergeur du
#: serveur ne bloque pas — contrairement aux ports de courriel (Franck, 12/11/2026).
JETON_GOOGLE = "https://oauth2.googleapis.com/token"
ENVOI_GMAIL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"

#: (adresse, données, en-têtes) → (code HTTP, corps). Remplaçable dans les essais.
Poste = Callable[[str, bytes, dict[str, str]], tuple[int, bytes]]


def _poster(adresse: str, donnees: bytes, entetes: dict[str, str]) -> tuple[int, bytes]:
    contexte = ssl.create_default_context(cafile=certifi.where())
    requete = urllib.request.Request(  # noqa: S310 - adresses https fixes ci-dessus
        adresse, data=donnees, headers=entetes, method="POST"
    )
    try:
        with urllib.request.urlopen(requete, timeout=30, context=contexte) as reponse:  # noqa: S310
            return reponse.status, reponse.read()
    except urllib.error.HTTPError as erreur:
        return erreur.code, erreur.read()


@dataclass
class GmailMessagerie:
    """Envoi par l'API de Gmail, depuis la boîte du praticien.

    L'accès ne porte que sur l'envoi (`gmail.send`) : Oris ne lit rien de la boîte. Le
    jeton durable vient d'un consentement donné une fois par le praticien
    (`scripts/autoriser_gmail.py`) et vit dans `.env`, jamais dans le dépôt.
    """

    client_id: str
    client_secret: str
    jeton_durable: str
    poster: Poste = _poster

    def _jeton_du_moment(self) -> str:
        corps = urllib.parse.urlencode(
            {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": self.jeton_durable,
                "grant_type": "refresh_token",
            }
        ).encode()
        try:
            code, reponse = self.poster(
                JETON_GOOGLE, corps, {"Content-Type": "application/x-www-form-urlencoded"}
            )
        except OSError as error:
            raise EnvoiImpossible("SMTP_UNAVAILABLE") from error
        if code in {400, 401}:
            # Accès retiré dans le compte Google, ou jeton expiré : il faut réautoriser.
            raise EnvoiImpossible("GMAIL_AUTH_FAILED")
        if code != 200:
            raise EnvoiImpossible("SMTP_UNAVAILABLE")
        jeton = json.loads(reponse).get("access_token")
        if not isinstance(jeton, str) or not jeton:
            raise EnvoiImpossible("GMAIL_AUTH_FAILED")
        return jeton

    def envoyer(self, message: EmailMessage) -> None:
        jeton = self._jeton_du_moment()
        brut = base64.urlsafe_b64encode(message.as_bytes()).decode()
        try:
            code, _ = self.poster(
                ENVOI_GMAIL,
                json.dumps({"raw": brut}).encode(),
                {"Authorization": f"Bearer {jeton}", "Content-Type": "application/json"},
            )
        except OSError as error:
            raise EnvoiImpossible("SMTP_UNAVAILABLE") from error
        if code == 200:
            return
        if code in {401, 403}:
            raise EnvoiImpossible("GMAIL_AUTH_FAILED")
        if code == 400:
            raise EnvoiImpossible("SMTP_RECIPIENT_REFUSED")
        raise EnvoiImpossible("SMTP_UNAVAILABLE")


@dataclass
class MessagerieMemoire:
    """Pour les tests : garde les messages au lieu de les envoyer."""

    envoyes: list[EmailMessage] = field(default_factory=list)

    def envoyer(self, message: EmailMessage) -> None:
        self.envoyes.append(message)


def messagerie_de(settings: Settings) -> Messagerie | None:
    """La boîte d'envoi configurée, ou rien si rien n'est branché.

    L'accès Gmail par le web passe en premier quand il est posé : l'hébergeur du serveur
    en ligne bloque les ports de courriel, pas le web."""
    if settings.gmail_refresh_token is not None and settings.gmail_client_id:
        return GmailMessagerie(
            settings.gmail_client_id,
            settings.gmail_client_secret.get_secret_value() if settings.gmail_client_secret else "",
            settings.gmail_refresh_token.get_secret_value(),
        )
    if settings.smtp_password is None or not settings.smtp_user:
        return None
    return SmtpMessagerie(
        settings.smtp_host,
        settings.smtp_port,
        settings.smtp_user,
        settings.smtp_password.get_secret_value(),
    )


def construire(
    expediteur: str,
    nom_expediteur: str,
    destinataire: str,
    objet: str,
    corps: str,
    piece: bytes,
    nom_piece: str,
    reference: UUID,
) -> EmailMessage:
    message = EmailMessage()
    message["From"] = f"{nom_expediteur} <{expediteur}>" if nom_expediteur else expediteur
    message["To"] = destinataire
    message["Subject"] = objet
    message["X-Oris-Document"] = str(reference)
    message.set_content(corps)
    message.add_attachment(piece, maintype="application", subtype="pdf", filename=nom_piece)
    return message
