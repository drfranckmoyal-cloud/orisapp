#!/usr/bin/env python3
"""Vectorise le nom « Oris » en Fraunces et réécrit les verrouillages du logo.

À exécuter **une fois**, et seulement si la police ou la graisse changent. Le
tracé produit est écrit en dur dans les SVG : ensuite, plus aucun fichier de la
marque ne dépend d'une police installée. C'est ce qui permet d'imprimer.

Réglages retenus :
- graisse 600 — le nom doit peser sans crier ;
- taille optique 48 — Fraunces resserre ses contrastes quand on monte, c'est la
  valeur qui tient aussi bien sur une plaque que dans un menu ;
- WONK désactivé — l'axe « biscornu » de Fraunces a du caractère, mais dans un
  logo il devient bavard. Une lettre plus tenue vieillit mieux.

Dépendance ponctuelle : `pip install fonttools`.

Usage :
  python3 scripts/vectoriser_nom.py
"""

from __future__ import annotations

from pathlib import Path

from fontTools.misc.transform import Transform
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

ROOT = Path(__file__).resolve().parent.parent
MARQUE = ROOT / "design" / "marque"
POLICE = MARQUE / "polices" / "Fraunces.ttf"
MOT = "Oris"
REGLAGES = {"wght": 600, "opsz": 48, "SOFT": 0, "WONK": 0}

VERT = "#14533B"
CREME = "#F6F3EE"
ENCRE = "#1C1A17"

# Le symbole, dans son carré de 120. Ses barres occupent y = 20 à 96.
BARRES = [
    (13, 38, 10, 34),
    (31, 20, 10, 76),
    (49, 30, 10, 48),
    (67, 20, 10, 76),
    (85, 38, 10, 34),
]
HAUT_BARRES, BAS_BARRES = 20, 96


def tracer_mot() -> tuple[str, float, float, float]:
    """Rend (tracé SVG, largeur, hauteur de capitale, profondeur des jambages)."""
    font = instantiateVariableFont(TTFont(POLICE), REGLAGES, inplace=True)
    glyphes = font.getGlyphSet()
    cmap = font.getBestCmap()
    hmtx = font["hmtx"]
    crenage: dict[tuple[str, str], int] = {}
    if "kern" in font:
        for table in font["kern"].kernTables:
            crenage.update(table.kernTable)

    noms = [cmap[ord(lettre)] for lettre in MOT]
    morceaux: list[str] = []
    avance = 0
    for index, nom in enumerate(noms):
        stylo = SVGPathPen(glyphes, ntos=lambda v: str(round(v)))
        # y inversé : en SVG l'axe descend, la ligne de base doit remonter.
        glyphes[nom].draw(TransformPen(stylo, Transform(1, 0, 0, -1, avance, 0)))
        if commandes := stylo.getCommands():
            morceaux.append(commandes)
        avance += hmtx[nom][0]
        if index + 1 < len(noms):
            avance += crenage.get((nom, noms[index + 1]), 0)

    # Boîte réelle de l'encre : c'est elle qu'on aligne, pas les métriques.
    bornes = BoundsPen(glyphes)
    decale = 0
    for index, nom in enumerate(noms):
        glyphes[nom].draw(TransformPen(bornes, Transform(1, 0, 0, 1, decale, 0)))
        decale += hmtx[nom][0]
        if index + 1 < len(noms):
            decale += crenage.get((nom, noms[index + 1]), 0)
    _, bas, droite, haut = bornes.bounds
    return " ".join(morceaux), droite, haut, -bas


def verrouillage(couleur: str, vertical: bool = False) -> str:
    """Compose symbole + nom, aux mêmes proportions que la planche."""
    tracé, largeur_mot, capitale, jambage = tracer_mot()

    hauteur_barres = BAS_BARRES - HAUT_BARRES  # 76 unités du carré de 120
    # Le nom fait 80 % de la hauteur des barres : il accompagne, il ne domine pas.
    echelle = (hauteur_barres * 0.80) / capitale
    mot_l = largeur_mot * echelle
    mot_h = (capitale + jambage) * echelle

    if vertical:
        ecart = 20
        largeur = max(120, mot_l)
        hauteur = 120 + ecart + mot_h
        x_symbole = (largeur - 120) / 2
        x_mot = (largeur - mot_l) / 2
        base = 120 + ecart + capitale * echelle
        groupes = (
            f'  <g transform="translate({x_symbole:.1f} 0)">\n{barres_svg()}  </g>\n'
            f'  <path transform="translate({x_mot:.1f} {base:.1f}) scale({echelle:.5f})"'
            f' d="{tracé}"/>\n'
        )
    else:
        ecart = 26
        largeur = 120 + ecart + mot_l
        hauteur = 120
        base = 60 + (capitale * echelle) / 2  # centré sur l'axe du symbole
        groupes = (
            f"{barres_svg()}"
            f'  <path transform="translate({120 + ecart:.1f} {base:.1f}) scale({echelle:.5f})"'
            f' d="{tracé}"/>\n'
        )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {largeur:.0f} {hauteur:.0f}" role="img" aria-label="Oris">\n'
        f"  <title>Oris</title>\n"
        f'  <g fill="{couleur}">\n{groupes}  </g>\n'
        f"</svg>\n"
    )


def barres_svg() -> str:
    return "".join(
        f'    <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{w / 2:g}"/>\n'
        for x, y, w, h in BARRES
    )


def main() -> int:
    if not POLICE.exists():
        print(f"Police absente : {POLICE.relative_to(ROOT)}")
        return 1
    fichiers = {
        "oris-logo-horizontal.svg": verrouillage(VERT),
        "oris-logo-vertical.svg": verrouillage(VERT, vertical=True),
        "oris-logo-blanc.svg": verrouillage(CREME),
        "oris-logo-monochrome.svg": verrouillage(ENCRE),
    }
    for nom, contenu in fichiers.items():
        (MARQUE / nom).write_text(contenu, encoding="utf-8")
        print(f"  {nom}")
    tracé, *_ = tracer_mot()
    (MARQUE / "oris-mot.txt").write_text(tracé + "\n", encoding="utf-8")
    print("  oris-mot.txt  (le tracé seul, pour réemploi)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
