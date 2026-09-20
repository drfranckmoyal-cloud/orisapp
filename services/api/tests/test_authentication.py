"""Jetons d'accès : exigés hors développement, révocables, jamais stockés en clair."""

from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from oris_api.config import Settings, get_settings
from oris_api.db.models import ApiToken, User
from oris_api.services import authentication
from oris_api.services.errors import Forbidden
from oris_api.services.identity import DEMO_EMAIL


def demo_user(api: Any, migrated_engine: Any) -> Any:
    api.get("/patients")  # crée le praticien de démonstration
    with Session(migrated_engine) as session:
        user = session.scalar(select(User).where(User.email == DEMO_EMAIL))
        assert user is not None
        return user.id


def issue(migrated_engine: Any, user_id: Any, label: str = "essai") -> str:
    with Session(migrated_engine) as session:
        token = authentication.issue(session, user_id, label)
        session.commit()
        return token.secret


def test_a_valid_token_identifies_the_practitioner(api: Any, migrated_engine: Any) -> None:
    secret = issue(migrated_engine, demo_user(api, migrated_engine))
    response = api.get("/patients", headers={"Authorization": f"Bearer {secret}"})
    assert response.status_code == 200


def test_the_secret_is_never_stored(api: Any, migrated_engine: Any) -> None:
    secret = issue(migrated_engine, demo_user(api, migrated_engine))
    with Session(migrated_engine) as session:
        rows = list(session.scalars(select(ApiToken)))
    assert rows and all(secret not in row.token_hash for row in rows)
    assert all(len(row.salt) == 32 for row in rows)
    # Deux jetons du même secret ne se ressemblent pas : le sel change.
    assert authentication.fingerprint(secret, "aa" * 16) != authentication.fingerprint(
        secret, "bb" * 16
    )


def test_an_unknown_token_is_refused(api: Any) -> None:
    response = api.get("/patients", headers={"Authorization": "Bearer oris_inconnu"})
    assert response.status_code == 403
    assert response.json()["code"] == "INVALID_TOKEN"


def test_a_revoked_token_opens_nothing(api: Any, migrated_engine: Any) -> None:
    user_id = demo_user(api, migrated_engine)
    secret = issue(migrated_engine, user_id)
    assert api.get("/patients", headers={"Authorization": f"Bearer {secret}"}).status_code == 200
    with Session(migrated_engine) as session:
        token = session.scalars(select(ApiToken)).one()
        authentication.revoke(session, token.id)
        session.commit()
    refused = api.get("/patients", headers={"Authorization": f"Bearer {secret}"})
    assert refused.status_code == 403 and refused.json()["code"] == "INVALID_TOKEN"


def test_outside_development_no_route_answers_without_a_token(api: Any) -> None:
    """Il n'existe pas de mode « ouvert » en production (docs/SECURITY.md)."""
    from oris_api.main import app

    app.dependency_overrides[get_settings] = lambda: Settings(app_env="production")
    try:
        response = api.get("/patients")
        assert response.status_code == 403
        assert response.json()["code"] == "AUTHENTICATION_REQUIRED"
    finally:
        app.dependency_overrides.pop(get_settings, None)


def test_a_token_without_the_oris_prefix_is_refused_before_any_lookup() -> None:
    with pytest.raises(Forbidden):
        authentication.actor_for(None, "jeton-au-hasard")  # type: ignore[arg-type]
