"""Fixtures communes. Les tests base de données visent une base dédiée."""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import OperationalError

REPO_ROOT = Path(__file__).resolve().parents[3]
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
