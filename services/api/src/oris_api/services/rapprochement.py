"""Reconnaître qu'un nom écrit ici et un nom écrit ailleurs désignent la même personne.

Le même patient s'écrit rarement pareil deux fois : Doctolib met « M. URBAN Eric »,
SmileCloud « Eric Urban », Oris « Éric URBAN ». Comparer caractère par caractère rate
la moitié des cas ; se contenter d'une ressemblance approximative en invente d'autres.
D'où deux seuils, et une zone entre les deux où **on demande au praticien**.

Cette mesure vient de Dental Lens (`attribution.py` du dépôt `smilecloud-photos`), où
elle tourne depuis septembre 2026 sur 772 dossiers réels. Elle est reprise telle quelle
pour que les deux applications reconnaissent les mêmes patients : une amélioration d'un
côté doit profiter à l'autre.

**La règle qui compte** : on ne tranche seul que sur des noms identiques — à l'ordre des
mots, aux accents, à la casse et aux espaces près. « Paul » et « Paule » se ressemblent
à 95 % et sont deux personnes. Rattacher des photos ou une consultation au mauvais
patient est pire qu'un doublon.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Literal

#: Au-dessus : c'est le même patient, on l'affirme.
SUR = 0.995
#: Au-dessus (mais sous `SUR`) : ça se ressemble, on demande. En dessous : sans rapport.
DOUTE = 0.72

Etat = Literal["trouve", "a_confirmer", "ambigu", "absent"]


def a_plat(texte: str) -> str:
    """Le nom réduit à ce qui compte : minuscules, sans accents, sans ponctuation."""
    sans = unicodedata.normalize("NFKD", texte or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", sans.lower()).strip()


def ressemblance(a: str, b: str) -> float:
    """De 0 à 1. L'ordre des mots est sans importance ; une lettre de différence coûte
    peu, un mot entier manquant coûte cher."""
    mots_a = a_plat(a).split()
    mots_b = a_plat(b).split()
    if not mots_a or not mots_b:
        return 0.0
    if sorted(mots_a) == sorted(mots_b):
        return 1.0

    # Chaque mot cherche son meilleur correspondant, et ne sert qu'une fois : sans quoi
    # « Jean Jean » ressemblerait parfaitement à « Jean Dupont ».
    reste = list(mots_b)
    total = 0.0
    for mot in mots_a:
        meilleur, choisi = 0.0, None
        for autre in reste:
            proche = SequenceMatcher(None, mot, autre).ratio()
            if proche > meilleur:
                meilleur, choisi = proche, autre
        if choisi is not None and meilleur >= 0.6:
            reste.remove(choisi)
            total += meilleur
    par_mots = total / max(len(mots_a), len(mots_b))

    # « DA SILVA » et « DASILVA » : le même nom, une espace en moins. On compare donc
    # aussi les noms collés, mots remis en ordre.
    colles = SequenceMatcher(None, "".join(sorted(mots_a)), "".join(sorted(mots_b))).ratio()
    return round(max(par_mots, colles), 3)


@dataclass(frozen=True, slots=True)
class Candidat:
    """Un rapprochement possible, avec de quoi le présenter au praticien."""

    cle: str
    nom: str
    pour_cent: int


@dataclass(frozen=True, slots=True)
class Proposition:
    """Ce qu'on peut dire d'un nom face à une liste de noms connus.

    - `trouve` : un seul correspondant certain — `cle` le désigne ;
    - `a_confirmer` : des noms qui ressemblent, aucun certain — le praticien tranche ;
    - `ambigu` : **plusieurs** correspondants certains, deux homonymes par exemple —
      le praticien tranche aussi, et surtout on ne choisit pas au hasard ;
    - `absent` : rien qui ressemble.
    """

    etat: Etat
    candidats: tuple[Candidat, ...] = ()

    @property
    def cle(self) -> str | None:
        return self.candidats[0].cle if self.etat == "trouve" else None

    @property
    def certain(self) -> bool:
        return self.etat == "trouve"


#: Au-delà, une liste de « ça pourrait être ceux-là » n'aide plus, elle noie.
MAX_CANDIDATS = 5


def proposer(nom: str, connus: Iterable[tuple[str, str]]) -> Proposition:
    """Rapproche `nom` d'une liste de `(clé, nom connu)`.

    La clé est ce qu'on veut retrouver : l'identifiant d'un patient d'Oris, celui d'un
    dossier SmileCloud. Cette fonction ne sait pas ce qu'elle désigne, et c'est voulu —
    elle sert aux deux.
    """
    notes = []
    for cle, connu in connus:
        note = ressemblance(connu, nom)
        if note >= DOUTE:
            notes.append((note, Candidat(cle=cle, nom=connu, pour_cent=round(note * 100))))
    notes.sort(key=lambda n: n[0], reverse=True)

    surs = tuple(c for note, c in notes if note >= SUR)
    if len(surs) == 1:
        return Proposition("trouve", surs)
    if len(surs) > 1:
        return Proposition("ambigu", surs)
    if notes:
        return Proposition("a_confirmer", tuple(c for _, c in notes[:MAX_CANDIDATS]))
    return Proposition("absent")
