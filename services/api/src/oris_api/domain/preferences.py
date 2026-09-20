"""Préférences de rédaction du praticien (spec §53, §123).

Elles changent la **forme** du compte rendu, jamais son contenu clinique : aucun fait
n'est ajouté, retiré ni modifié par une préférence. Tout est réversible (§177).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

DocumentLength = Literal["standard", "concise"]


class PractitionerPreferences(BaseModel):
    """Ce que le praticien a choisi. Les valeurs par défaut sont celles d'Oris."""

    model_config = ConfigDict(extra="forbid")

    document_length: DocumentLength = "standard"
    # concept Oris -> mot préféré du praticien (« extraction » -> « avulsion »).
    terminology: dict[str, str] = Field(default_factory=dict, max_length=200)

    @classmethod
    def load(cls, stored: dict[str, Any] | None) -> PractitionerPreferences:
        """Lit les préférences enregistrées ; un contenu illisible revient aux défauts."""
        if not stored:
            return cls()
        try:
            return cls.model_validate(stored)
        except ValueError:
            return cls()


class PreferencesPatch(BaseModel):
    """Modification partielle : seuls les champs fournis changent."""

    model_config = ConfigDict(extra="forbid")

    document_length: DocumentLength | None = None
    terminology: dict[str, str] | None = None

    def applied_to(self, current: PractitionerPreferences) -> PractitionerPreferences:
        changes = self.model_dump(exclude_none=True)
        return current.model_copy(update=changes)
