"""Santé de l'API."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from oris_api.db.session import get_session
from oris_api.main import app


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_health_reports_mock_providers(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert set(body["providers"].values()) == {"mock"}
    assert response.headers["X-Request-ID"]


def test_ready_when_database_reachable(client: TestClient, db_engine: Engine) -> None:
    def session_override() -> Iterator[Session]:
        with sessionmaker(bind=db_engine)() as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "ok"}


def test_not_ready_when_database_unreachable(client: TestClient) -> None:
    from sqlalchemy import create_engine

    dead = create_engine("postgresql+psycopg://oris:oris@127.0.0.1:1/none?connect_timeout=1")

    def session_override() -> Iterator[Session]:
        with sessionmaker(bind=dead)() as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "unavailable", "database": "unreachable"}


def test_openapi_is_generated(client: TestClient) -> None:
    assert "/health" in client.get("/openapi.json").json()["paths"]
