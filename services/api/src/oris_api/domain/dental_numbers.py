"""Numéros de dents dits en toutes lettres → chiffres FDI (spec §16.1).

« vingt-six », « vingt six » → 26. Sert à comparer les transcriptions (banc d'essai)
et, plus tard, à la normalisation clinique. Ne convertit que des nombres qui sont des
numéros FDI valides ; le contexte clinique (est-ce bien une dent ?) reste l'affaire de
l'extraction (M5).
"""

from __future__ import annotations

import re

UNITS = {
    "un": 1, "une": 1, "deux": 2, "trois": 3, "quatre": 4, "cinq": 5,
    "six": 6, "sept": 7, "huit": 8, "neuf": 9,
}  # fmt: skip
TEENS = {"onze": 11, "douze": 12, "treize": 13, "quatorze": 14, "quinze": 15, "seize": 16}
TENS = {"dix": 10, "vingt": 20, "trente": 30, "quarante": 40, "cinquante": 50,
        "soixante": 60}  # fmt: skip

FDI = re.compile(r"^(?:1[1-8]|2[1-8]|3[1-8]|4[1-8]|5[1-5]|6[1-5]|7[1-5]|8[1-5])$")


def words_to_number(words: list[str]) -> tuple[int, int] | None:
    """Nombre lu au début de `words` et nombre de mots consommés."""
    if not words:
        return None
    first = words[0]
    if first in TEENS:
        return TEENS[first], 1
    if first == "dix" and len(words) > 1 and words[1] in {"sept", "huit"}:
        return 10 + UNITS[words[1]], 2
    if first in TENS and first != "dix":
        value = TENS[first]
        rest = words[1:]
        if rest[:2] == ["et", "un"]:
            return value + 1, 3
        if rest and rest[0] in UNITS and rest[0] not in {"un", "une"}:
            return value + UNITS[rest[0]], 2
        if first == "soixante" and rest and rest[0] in TEENS:
            return 60 + TEENS[rest[0]], 2
        return value, 1
    if first in {"quatre"} and words[1:2] == ["vingt"]:
        tail = words[2:]
        if tail and tail[0] in UNITS:
            return 80 + UNITS[tail[0]], 3
        return 80, 2
    return None


def normalize_tooth_numbers(tokens: list[str]) -> list[str]:
    """Remplace les nombres écrits en lettres correspondant à un numéro FDI par des chiffres."""
    output: list[str] = []
    index = 0
    while index < len(tokens):
        parsed = words_to_number(tokens[index:])
        if parsed and FDI.match(str(parsed[0])):
            output.append(str(parsed[0]))
            index += parsed[1]
        else:
            output.append(tokens[index])
            index += 1
    return output


def tooth_mentions(tokens: list[str]) -> list[str]:
    return [token for token in tokens if FDI.match(token)]


# --- Une dent, ou un nombre qui lui ressemble ? --------------------------------------
#
# Un numéro FDI (11-48, 51-85) ne se distingue d'un âge, d'un score ou d'une quantité que
# par ce qui l'entoure. Confondre les deux a un coût concret : le 4 octobre 2026, le
# compte rendu d'une patiente était impossible à valider parce qu'« un score BEWE à 16 »,
# « entre 17 et 20 ans » et « depuis l'âge de 18 ans » étaient lus comme les dents 16, 17
# et 18. Une alerte qui crie au loup apprend au praticien à ignorer les alertes.

NOMBRE_FDI = re.compile(r"(?<![\d,.])([1-4][1-8]|[5-8][1-5])(?![\d,.]\d)")

#: Ce qui suit un nombre et prouve que ce n'est pas une dent : une unité, une quantité.
UNITES = {
    "an", "ans", "année", "années", "mois", "semaine", "semaines", "jour", "jours",
    "heure", "heures", "minute", "minutes", "seconde", "secondes", "fois",
    "cigarettes", "cigarette", "verres", "verre", "unités", "unité",
    "mm", "cm", "ml", "mg", "g", "kg", "%", "€", "euros", "euro",
    "séances", "séance", "consultations", "consultation", "rendez-vous",
}  # fmt: skip

#: Ce qui précède un nombre et prouve que c'est une mesure : un score, un âge, un stade.
ECHELLES = {
    "bewe", "score", "scores", "indice", "échelle", "echelle", "stade", "grade",
    "note", "âge", "age", "classe", "niveau", "pourcentage",
}  # fmt: skip

#: « entre 17 et 20 ans » : l'unité du second nombre vaut aussi pour le premier.
LIAISONS = {"et", "à", "a", "ou", "-", "puis"}

MOTS = re.compile(r"[\w%€'-]+", re.UNICODE)
PORTEE_AVANT = 4
PORTEE_APRES = 3


def _mots_autour(texte: str, debut: int, fin: int) -> tuple[list[str], list[str]]:
    avant = [m.group(0).lower() for m in MOTS.finditer(texte[:debut])][-PORTEE_AVANT:]
    apres = [m.group(0).lower() for m in MOTS.finditer(texte[fin:])][:PORTEE_APRES]
    return avant, apres


def _est_une_mesure(avant: list[str], apres: list[str]) -> bool:
    if apres and apres[0] in UNITES:
        return True
    # « 17 et 20 ans » : l'unité arrive après le second nombre de l'énumération.
    if len(apres) >= 3 and apres[0] in LIAISONS and apres[1].isdigit() and apres[2] in UNITES:
        return True
    return any(mot.strip("'’") in ECHELLES for mot in avant)


def dents_citees(texte: str) -> set[str]:
    """Numéros de dents réellement cités dans une phrase rédigée.

    Large par choix : une dent écrite sans appui est un risque clinique, mieux vaut la
    signaler. Mais un nombre entouré d'une unité (« 18 ans », « 10 cigarettes ») ou d'une
    échelle (« score BEWE à 16 ») n'est pas une dent, et ne doit jamais bloquer.
    """
    citees: set[str] = set()
    for trouve in NOMBRE_FDI.finditer(texte):
        avant, apres = _mots_autour(texte, trouve.start(1), trouve.end(1))
        if not _est_une_mesure(avant, apres):
            citees.add(trouve.group(1))
    return citees
