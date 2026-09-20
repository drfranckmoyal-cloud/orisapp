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
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from oris_api.db.models import ApiToken, OrganizationMember, User
from oris_api.services.errors import Forbidden, NotFound
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
