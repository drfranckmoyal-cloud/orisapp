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
