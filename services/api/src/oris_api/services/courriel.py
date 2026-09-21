"""Envoi des documents par courriel.

Oris envoie depuis la boîte du praticien (SMTP, par exemple Gmail avec un mot de passe
d'application rangé dans `.env`). Chaque destinataire reçoit **son propre** message :
aucun ne voit l'adresse des autres. Chaque envoi réussi est noté comme un envoi du
document (« Envoyé à … »), avec le canal courriel.

Le contenu part hors d'Oris : c'est un geste du praticien, jamais automatique, et le
journal d'audit n'en garde que des identifiants.
"""

from __future__ import annotations

import smtplib
import ssl
from dataclasses import dataclass, field
from email.message import EmailMessage
from typing import Protocol
from uuid import UUID

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
        contexte = ssl.create_default_context()
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


@dataclass
class MessagerieMemoire:
    """Pour les tests : garde les messages au lieu de les envoyer."""

    envoyes: list[EmailMessage] = field(default_factory=list)

    def envoyer(self, message: EmailMessage) -> None:
        self.envoyes.append(message)


def messagerie_de(settings: Settings) -> Messagerie | None:
    """La boîte d'envoi configurée, ou rien si le mot de passe manque."""
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
