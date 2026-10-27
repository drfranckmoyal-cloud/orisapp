"""La civilité du patient, et ce qu'elle permet d'accorder.

Franck, le 27/10/2026 : « c'est un patient et pas une patiente ». Oris ne savait pas :
la fiche ne portait ni Monsieur ni Madame, et le rédacteur devinait le genre d'après le
prénom. Un prénom n'est pas un genre — et un compte rendu qui se trompe de genre fait
douter de tout le reste.

La civilité est une donnée de **forme** : elle ne change aucun fait clinique, elle ne
sert qu'à accorder. Inconnue, Oris écrit sans accorder plutôt que de parier.
"""

from __future__ import annotations

from typing import Literal, get_args

Civilite = Literal["", "monsieur", "madame"]

#: Les valeurs admises en base, la vide comprise : « on ne sait pas » est une réponse.
CIVILITES: tuple[str, ...] = get_args(Civilite)

LIBELLES: dict[str, str] = {
    "": "Non précisée",
    "monsieur": "Monsieur",
    "madame": "Madame",
}

#: Ce qu'on dit au rédacteur. Sans civilité, la consigne est de **ne pas** accorder.
CONSIGNES: dict[str, str] = {
    "monsieur": "Le patient est un homme : accorde au masculin (« le patient », « il »).",
    "madame": "La patiente est une femme : accorde au féminin (« la patiente », « elle »).",
    "": (
        "La civilité du patient n'est pas connue : n'accorde pas au genre. Écris « le "
        "patient » (forme neutre d'usage) et évite « il », « elle », « venue », « venu ». "
        "Ne devine jamais le genre d'après le prénom."
    ),
}


def consigne(civilite: str) -> str:
    """La consigne d'accord, pour une civilité connue ou non."""
    return CONSIGNES.get(civilite, CONSIGNES[""])


def libelle(civilite: str) -> str:
    return LIBELLES.get(civilite, LIBELLES[""])
