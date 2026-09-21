"""Fixtures communes. Les tests base de données visent une base dédiée."""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import OperationalError

REPO_ROOT = Path(__file__).resolve().parents[3]

# Les tests n'utilisent jamais les réglages privés du poste (services/api/.env) :
# aucun fournisseur externe, quelles que soient les clés présentes.
os.environ["STT_PROVIDER"] = "mock"
os.environ["CLINICAL_EXTRACTION_PROVIDER"] = "mock"
os.environ["ALLOW_EXTERNAL_STT"] = "false"
os.environ["ALLOW_EXTERNAL_LLM"] = "false"
# La rédaction par Claude est testée avec un modèle simulé, jamais celle du poste.
os.environ["DOCUMENT_GENERATION_PROVIDER"] = "mock"
# Aucun courriel ne part d'un test : la boîte du poste n'est jamais utilisée.
os.environ["SMTP_PASSWORD"] = ""
os.environ["SMTP_USER"] = ""
# L'écoute en direct est injectée par les tests qui la veulent, jamais héritée du poste.
os.environ["ENABLE_LIVE_TRANSCRIPT"] = "false"
# Les journées déposées par les tests vivent dans un dossier jetable, jamais celui du poste.
os.environ["JOURNEE_DIR"] = str(Path(tempfile.mkdtemp(prefix="oris-journees-")))
os.environ["SMILECLOUD_DIR"] = str(Path(tempfile.mkdtemp(prefix="oris-smilecloud-")))
# Les pièces jointes des tests vivent dans un dossier jetable, jamais celui du poste.
os.environ["ATTACHMENT_DIR"] = str(Path(tempfile.mkdtemp(prefix="oris-pieces-")))
os.environ["APP_ENV"] = "local"
DEFAULT_TEST_DATABASE_URL = "postgresql+psycopg://oris:oris@localhost:5432/oris_test"


def load_jsonl(relative: str) -> list[dict[str, Any]]:
    path = REPO_ROOT / relative
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


@pytest.fixture(scope="session")
def corpus_cases() -> list[dict[str, Any]]:
    return load_jsonl("corpus/synthetic_consultations_100.jsonl")


@pytest.fixture(scope="session")
def critical_cases() -> list[dict[str, Any]]:
    return load_jsonl("evals/critical_regression_cases.jsonl")


@pytest.fixture(scope="session")
def test_database_url() -> str:
    return os.environ.get("ORIS_TEST_DATABASE_URL", DEFAULT_TEST_DATABASE_URL)


@pytest.fixture(scope="session")
def db_engine(test_database_url: str) -> Iterator[Engine]:
    engine = create_engine(test_database_url)
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except OperationalError:
        pytest.fail(
            "Base de test injoignable. Lancer : "
            "services/api/.venv/bin/python scripts/dev_postgres.py start "
            "(ou docker compose -f infra/docker/docker-compose.yml up -d)."
        )
    yield engine
    engine.dispose()


# --- API sur base de test ------------------------------------------------------------

API_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def migrated_engine(db_engine: Engine, test_database_url: str) -> Engine:
    from alembic.config import Config

    from alembic import command

    config = Config(str(API_ROOT / "alembic.ini"))
    config.attributes["database_url"] = test_database_url
    config.attributes["configure_logger"] = False
    command.upgrade(config, "head")
    return db_engine


def truncate_all(engine: Engine) -> None:
    with engine.begin() as connection:
        tables = connection.execute(
            text(
                "SELECT quote_ident(schemaname) || '.' || quote_ident(tablename) FROM pg_tables "
                "WHERE schemaname IN ('public', 'learning') AND tablename <> 'alembic_version'"
            )
        ).scalars()
        names = ", ".join(tables)
        if names:
            connection.execute(text(f"TRUNCATE {names} CASCADE"))


@pytest.fixture
def api(migrated_engine: Engine) -> Iterator[Any]:
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import Session, sessionmaker

    from oris_api.db.session import get_session
    from oris_api.main import app

    truncate_all(migrated_engine)
    factory = sessionmaker(bind=migrated_engine, expire_on_commit=False)

    def session_override() -> Iterator[Session]:
        with factory() as session:
            yield session

    from oris_api.services.audio_sink import MemoryAudioSink

    app.dependency_overrides[get_session] = session_override
    original_sink = app.state.audio_sink
    app.state.audio_sink = MemoryAudioSink()
    with TestClient(app) as client:
        yield client
    app.state.audio_sink = original_sink
    app.dependency_overrides.clear()
    truncate_all(migrated_engine)


@pytest.fixture
def db_session(api: Any, migrated_engine: Engine) -> Iterator[Any]:
    """Lecture directe de la base, sur la même base propre que `api`.

    Dépend de `api` pour hériter de son nettoyage : un test qui compte des lignes
    compte celles qu'il a écrites, pas celles du test précédent.
    """
    from sqlalchemy.orm import sessionmaker

    factory = sessionmaker(bind=migrated_engine, expire_on_commit=False)
    with factory() as session:
        yield session


def run_synthetic(api: Any, case_id: str) -> dict[str, Any]:
    response = api.post(f"/synthetic-cases/{case_id}/encounters")
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


def documents_by_type(api: Any, encounter_id: str) -> dict[str, dict[str, Any]]:
    response = api.get(f"/encounters/{encounter_id}/documents")
    assert response.status_code == 200, response.text
    return {doc["document_type"]: doc for doc in response.json()}


def clinical_object(api: Any, encounter_id: str) -> dict[str, Any]:
    response = api.get(f"/encounters/{encounter_id}/clinical-object")
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()["clinical_object"]
    return body
