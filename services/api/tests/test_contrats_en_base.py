"""La base accepte exactement ce que le contrat clinique nomme.

Le 27/10/2026, deux consultations réelles ont été perdues à l'enregistrement : le contrat
avait gagné les catégories `patient_context` et `anamnesis` le 10 octobre, le modèle
Python les avait prises toutes seules (`contract_enum` lit le contrat), et **aucune
migration ne les avait portées en base**. La relecture aboutissait, puis la base refusait
le premier fait, et l'écran annonçait « Extraction refusée » — un mensonge.

Ce test compare chaque énumération du contrat à la contrainte qui la garde en base. Un
écart échoue ici, en une seconde, au lieu d'attendre une vraie consultation.
"""

from __future__ import annotations

import re

from sqlalchemy import Engine, Enum, text

from oris_api.db import models  # noqa: F401 - enregistre les tables sur Base
from oris_api.db.base import Base


def enumerations_du_contrat() -> dict[str, tuple[str, list[str]]]:
    """Pour chaque colonne gardée par une liste de valeurs : nom de contrainte → valeurs."""
    attendues: dict[str, tuple[str, list[str]]] = {}
    for table in Base.metadata.tables.values():
        for colonne in table.columns:
            type_ = colonne.type
            if isinstance(type_, Enum) and type_.create_constraint:
                nom = f"ck_{table.name}_{type_.name}"
                attendues[nom] = (f"{table.name}.{colonne.name}", list(type_.enums))
    return attendues


def valeurs_en_base(engine: Engine) -> dict[str, set[str]]:
    with engine.connect() as connection:
        definitions = connection.execute(
            text(
                "SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint WHERE contype = 'c'"
            )
        ).all()
    return {
        nom: set(re.findall(r"'([^']+)'::character varying", definition))
        for nom, definition in definitions
    }


def test_la_base_connait_toutes_les_valeurs_du_contrat(migrated_engine: Engine) -> None:
    attendues = enumerations_du_contrat()
    assert attendues, "aucune énumération trouvée : le test ne garde plus rien"

    en_base = valeurs_en_base(migrated_engine)
    ecarts: list[str] = []
    for contrainte, (colonne, valeurs) in sorted(attendues.items()):
        presentes = en_base.get(contrainte)
        if presentes is None:
            ecarts.append(f"{colonne} : contrainte {contrainte} absente de la base")
            continue
        manquent = [valeur for valeur in valeurs if valeur not in presentes]
        en_trop = sorted(presentes - set(valeurs))
        if manquent:
            ecarts.append(f"{colonne} : la base refuse {', '.join(manquent)}")
        if en_trop:
            ecarts.append(f"{colonne} : la base accepte encore {', '.join(en_trop)}")

    assert not ecarts, "contrat et base ne disent plus la même chose :\n" + "\n".join(ecarts)


def test_les_deux_rubriques_du_modele_de_consultation_passent(migrated_engine: Engine) -> None:
    """Les deux catégories qui ont coûté deux consultations, nommément."""
    presentes = valeurs_en_base(migrated_engine)["ck_clinical_facts_fact_category"]
    assert {"patient_context", "anamnesis"} <= presentes
