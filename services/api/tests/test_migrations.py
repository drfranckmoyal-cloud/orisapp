"""Les migrations montent, descendent et correspondent aux modèles."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import Engine, inspect, text
from sqlalchemy.exc import IntegrityError

from alembic import command
from oris_api.db.base import Base

API_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def alembic_config(test_database_url: str, db_engine: Engine) -> Iterator[Config]:
    config = Config(str(API_ROOT / "alembic.ini"))
    config.attributes["database_url"] = test_database_url
    config.attributes["configure_logger"] = False
    command.downgrade(config, "base")
    yield config
    # Les autres tests attendent une base à jour.
    command.upgrade(config, "head")


def test_upgrade_downgrade_upgrade(alembic_config: Config, db_engine: Engine) -> None:
    command.upgrade(alembic_config, "head")
    tables = set(inspect(db_engine).get_table_names())
    assert {"patients", "encounters", "clinical_facts", "documents"} <= tables
    assert inspect(db_engine).get_table_names(schema="learning") == ["learning_events"]
    command.downgrade(alembic_config, "base")
    assert set(inspect(db_engine).get_table_names()) <= {"alembic_version"}
    command.upgrade(alembic_config, "head")


def test_models_match_migrations(alembic_config: Config, db_engine: Engine) -> None:
    command.upgrade(alembic_config, "head")
    with db_engine.connect() as connection:
        context = MigrationContext.configure(connection, opts={"include_schemas": True})
        assert compare_metadata(context, Base.metadata) == []


def test_contract_enums_are_enforced_by_database(alembic_config: Config, db_engine: Engine) -> None:
    command.upgrade(alembic_config, "head")
    with db_engine.connect() as connection, pytest.raises(IntegrityError):
        connection.execute(
            text(
                "INSERT INTO learning.learning_events (id, organization_id, user_id, "
                "encounter_id, event_type, scope, source_version, validated_by_practitioner, "
                "eligible_for_global_learning, learning_status) VALUES (gen_random_uuid(), "
                "gen_random_uuid(), gen_random_uuid(), gen_random_uuid(), 'invented_type', "
                "'user', 'v1', false, false, 'captured')"
            )
        )
