"""Base déclarative SQLAlchemy et colonnes communes."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, get_args
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, MetaData, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def utcnow() -> datetime:
    return datetime.now(UTC)


def uuid_pk() -> Mapped[UUID]:
    return mapped_column(primary_key=True, default=uuid4)


def created_at() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), default=utcnow, server_default=func.now())


def updated_at() -> Mapped[datetime]:
    return mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, server_default=func.now()
    )


def contract_enum(literal: Any, name: str) -> Enum:
    """Colonne texte + contrainte CHECK dont les valeurs viennent des schémas.

    `literal` est un alias `Literal[...]` de contracts/generated.py : les valeurs
    admises en base sont celles du contrat, sans copie manuelle.
    """
    values = get_args(literal)
    if not values:
        raise ValueError(f"{name}: alias Literal attendu")
    return Enum(
        *values,
        name=name,
        native_enum=False,
        create_constraint=True,
        length=max(len(v) for v in values),
        validate_strings=True,
    )
