"""Préférences de rédaction du praticien (spec §53, §123).

Elles changent la **forme** du compte rendu, jamais son contenu clinique : aucun fait
n'est ajouté, retiré ni modifié par une préférence. Tout est réversible (§177).
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

DocumentLength = Literal["standard", "concise"]

#: Une consigne tient en une phrase : au-delà, ce n'est plus une consigne de forme.
Consigne = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=240)]
CONSIGNES_MAX = 20


def ajouter_consigne(consignes: list[str], nouvelle: str) -> list[str]:
    """La liste avec la consigne en plus, sans doublon ; les plus anciennes cèdent la place."""
    propre = " ".join(nouvelle.split())
    reste = [c for c in consignes if c.casefold() != propre.casefold()]
    return [*reste, propre][-CONSIGNES_MAX:]


class PractitionerPreferences(BaseModel):
    """Ce que le praticien a choisi. Les valeurs par défaut sont celles d'Oris."""

    model_config = ConfigDict(extra="forbid")

    document_length: DocumentLength = "standard"
    # concept Oris -> mot préféré du praticien (« extraction » -> « avulsion »).
    terminology: dict[str, str] = Field(default_factory=dict, max_length=200)
    # Consignes de forme dites une fois, appliquées à tous les documents suivants
    # (« attribue une fois par paragraphe », « phrases courtes »). Elles ne portent que
    # sur la forme : le rédacteur les suit tant qu'elles ne touchent à aucun fait, et ses
    # garde-fous s'appliquent après comme avant.
    consignes: list[Consigne] = Field(default_factory=list, max_length=CONSIGNES_MAX)

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
    consignes: list[Consigne] | None = None

    def applied_to(self, current: PractitionerPreferences) -> PractitionerPreferences:
        changes = self.model_dump(exclude_none=True)
        return current.model_copy(update=changes)
