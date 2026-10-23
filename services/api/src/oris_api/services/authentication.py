"""Jetons d'accès (docs/SECURITY.md).

Hors développement, aucune route métier ne répond sans jeton valide. Le secret n'est
affiché qu'une fois, à l'émission : la base ne contient qu'une empreinte scrypt, donc
un vol de base ne rend aucun jeton utilisable.

Ce n'est **pas** une authentification à deux facteurs : elle viendra d'un fournisseur
d'identité, au moment de l'hébergement agréé. C'est écrit dans les limites connues.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from oris_api.db.models import ApiToken, OrganizationMember, User
from oris_api.services.errors import Forbidden, NotFound, Unprocessable
from oris_api.services.identity import Actor

PREFIX = "oris_"
SECRET_BYTES = 32
SCRYPT = {"n": 2**14, "r": 8, "p": 1, "dklen": 32}


@dataclass(frozen=True)
class IssuedToken:
    """Le secret n'existe qu'ici, une seule fois."""

    token_id: UUID
    secret: str
    label: str


def fingerprint(secret: str, salt: str) -> str:
    derived = hashlib.scrypt(secret.encode(), salt=bytes.fromhex(salt), **SCRYPT)
    return derived.hex()


def issue(session: Session, user_id: UUID, label: str) -> IssuedToken:
    user = session.get(User, user_id)
    if user is None:
        raise NotFound("USER_NOT_FOUND", str(user_id))
    secret = PREFIX + secrets.token_urlsafe(SECRET_BYTES)
    salt = secrets.token_hex(16)
    token = ApiToken(
        user_id=user_id,
        label=label[:100] or "jeton",
        token_hash=fingerprint(secret, salt),
        salt=salt,
    )
    session.add(token)
    session.flush()
    return IssuedToken(token_id=token.id, secret=secret, label=token.label)


def revoke(session: Session, token_id: UUID) -> ApiToken:
    token = session.get(ApiToken, token_id)
    if token is None:
        raise NotFound("TOKEN_NOT_FOUND", str(token_id))
    if token.revoked_at is None:
        token.revoked_at = datetime.now(UTC)
        session.flush()
    return token


def actor_for(session: Session, presented: str) -> Actor:
    """Jeton présenté -> praticien, ou refus. Aucune fuite d'information au passage."""
    if not presented.startswith(PREFIX):
        raise Forbidden("INVALID_TOKEN")
    # Comparaison en temps constant, sur toutes les empreintes actives.
    for token in session.scalars(select(ApiToken).where(ApiToken.revoked_at.is_(None))):
        if hmac.compare_digest(token.token_hash, fingerprint(presented, token.salt)):
            token.last_used_at = datetime.now(UTC)
            member = session.scalar(
                select(OrganizationMember).where(OrganizationMember.user_id == token.user_id)
            )
            if member is None:
                raise Forbidden("NO_ORGANIZATION")
            session.flush()
            return Actor(member.organization_id, token.user_id)
    raise Forbidden("INVALID_TOKEN")


# --- Mot de passe du praticien (étape 1 de la commercialisation) ----------------------
#
# Le jeton reste ce qui circule à chaque appel : c'est lui qui a fait ses preuves. Ce qui
# change, c'est la façon de l'obtenir — en se connectant, au lieu de le recopier à la
# main depuis le Mac. Franck, le 24/10/2026 : « j'en ai marre de mettre des jetons ».

#: En deçà, un mot de passe se devine. Au-delà de ce seuil, c'est le blocage qui protège.
LONGUEUR_MOT_DE_PASSE_MIN = 10
#: Essais manqués d'affilée avant que le compte ne cesse de répondre…
ESSAIS_AVANT_BLOCAGE = 5
#: …et pour combien de temps. Assez pour rendre la devinette vaine, assez peu pour ne pas
#: enfermer dehors un praticien qui s'est trompé de casse.
BLOCAGE = timedelta(minutes=15)


class MotDePasseRefuse(Forbidden):
    """Identifiants faux, compte sans mot de passe, ou compte bloqué."""


def poser_mot_de_passe(session: Session, user: User, mot_de_passe: str) -> None:
    """Pose ou remplace le mot de passe d'un praticien, et débloque son compte."""
    if len(mot_de_passe) < LONGUEUR_MOT_DE_PASSE_MIN:
        raise Unprocessable("PASSWORD_TOO_SHORT", str(LONGUEUR_MOT_DE_PASSE_MIN))
    salt = secrets.token_hex(16)
    user.password_salt = salt
    user.password_hash = fingerprint(mot_de_passe, salt)
    user.failed_logins = 0
    user.locked_until = None
    session.flush()


def _bloque(user: User, maintenant: datetime) -> bool:
    return user.locked_until is not None and user.locked_until > maintenant


def connecter(
    session: Session,
    email: str,
    mot_de_passe: str,
    appareil: str,
    maintenant: datetime | None = None,
) -> tuple[User, IssuedToken]:
    """Vérifie les identifiants et délivre un jeton pour **cet appareil-là**.

    Un jeton par appareil : perdre son téléphone ne coûte que ce jeton-là, qui se révoque
    seul. Le motif du refus n'est jamais détaillé à l'appelant — compte inconnu, sans mot
    de passe ou mot de passe faux se ressemblent de l'extérieur, sinon on apprend à qui
    écrire.
    """
    instant = maintenant or datetime.now(UTC)
    user = session.scalar(select(User).where(User.email == email.strip().lower()))
    if user is None or not user.password_hash or not user.password_salt:
        raise MotDePasseRefuse("IDENTIFIANTS_REFUSES")
    if _bloque(user, instant):
        raise MotDePasseRefuse("COMPTE_BLOQUE")
    if not hmac.compare_digest(fingerprint(mot_de_passe, user.password_salt), user.password_hash):
        user.failed_logins += 1
        if user.failed_logins >= ESSAIS_AVANT_BLOCAGE:
            user.locked_until = instant + BLOCAGE
        # Le compte des essais manqués doit **survivre au refus** : une requête qui échoue
        # est annulée, et le compteur repartait donc de zéro à chaque fois — le blocage ne
        # se déclenchait jamais, et la devinette restait gratuite.
        session.commit()
        raise MotDePasseRefuse("IDENTIFIANTS_REFUSES")
    user.failed_logins = 0
    user.locked_until = None
    return user, issue(session, user.id, appareil or "appareil")
