"""Rend à la base les deux rubriques de faits ajoutées au contrat le 10 octobre.

Le 10/10/2026, le modèle de compte rendu de première consultation a gagné deux rubriques
— « Situation » et « Anamnèse » — et le contrat clinique deux catégories de faits,
`patient_context` et `anamnesis`. Le modèle Python les a prises sans rien à écrire
(`contract_enum` lit le contrat), mais **la contrainte en base n'a jamais été migrée**.

Conséquence, le 27/10/2026 : deux consultations réelles, 16 et 9 minutes, transcrites et
relues par Claude — puis **perdues à l'enregistrement**, la base refusant le premier fait
rangé en `patient_context`. L'écran disait « Extraction refusée », ce qui était faux : la
relecture avait abouti.

Un test (`test_contrats_en_base.py`) compare désormais les vingt-quatre énumérations du
contrat à celles de la base : un écart de ce genre ne peut plus passer en silence.

Revision ID: 0023
Revises: 0022
Create Date: 2026-10-27 13:00:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0023"
down_revision: str | None = "0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Le nom court : la convention de nommage d'Alembic ajoute « ck_clinical_facts_ ».
CONTRAINTE = "fact_category"

AVANT = (
    "chief_complaint",
    "history",
    "symptom",
    "clinical_finding",
    "radiographic_finding",
    "assessment",
    "diagnosis",
    "treatment_option",
    "treatment_decision",
    "procedure",
    "material",
    "medication",
    "patient_information",
    "follow_up",
    "other",
)

APRES = (
    "patient_context",
    "chief_complaint",
    "history",
    "anamnesis",
    "symptom",
    "clinical_finding",
    "radiographic_finding",
    "assessment",
    "diagnosis",
    "treatment_option",
    "treatment_decision",
    "procedure",
    "material",
    "medication",
    "patient_information",
    "follow_up",
    "other",
)


def _poser(valeurs: tuple[str, ...]) -> None:
    liste = ", ".join(f"'{valeur}'" for valeur in valeurs)
    op.drop_constraint(CONTRAINTE, "clinical_facts", type_="check")
    op.create_check_constraint(CONTRAINTE, "clinical_facts", f"category IN ({liste})")


def upgrade() -> None:
    _poser(APRES)


def downgrade() -> None:
    op.execute(
        "UPDATE clinical_facts SET category = 'other' "
        "WHERE category IN ('patient_context', 'anamnesis')"
    )
    _poser(AVANT)
