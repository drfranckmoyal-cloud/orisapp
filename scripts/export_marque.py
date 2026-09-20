#!/usr/bin/env python3
"""Exporte la marque Oris en PNG, à toutes les tailles utiles.

Le symbole n'est fait que de rectangles arrondis : on le dessine directement, à
quatre fois la taille voulue, puis on réduit. Le rendu est net à 16 px sans
dépendre d'un moteur SVG installé sur la machine.

Le mot « Oris » n'est pas exporté : il demande la police définitive vectorisée.
Les verrouillages restent en SVG jusque-là.

Usage :
  python3 scripts/export_marque.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
SORTIE = ROOT / "design" / "marque" / "png"

VERT = (20, 83, 59, 255)
VERT_FONCE = (14, 58, 41, 255)
CREME = (246, 243, 238, 255)
ENCRE = (26, 24, 21, 255)
TRANSPARENT = (0, 0, 0, 0)

# Le geste, dans un carré de 120 : x, haut, largeur, hauteur.
# Le profil du haut dessine la couronne, celui du bas les racines.
BARRES = [
    (13, 38, 10, 34),
    (31, 20, 10, 76),
    (49, 30, 10, 48),
    (67, 20, 10, 76),
    (85, 38, 10, 34),
]
# À 16 px, cinq barres se referment. Trois suffisent : deux cuspides, un sillon.
TROIS = [
    (18, 26, 16, 56),
    (44, 40, 16, 28),
    (70, 26, 16, 56),
]
SUPER = 4  # on dessine en grand, on réduit : les arrondis restent propres


def dessiner(
    taille: int,
    barres: list[tuple[int, int, int, int]],
    encre,
    fond=TRANSPARENT,
    rayon_fond: float = 0.0,
    marge: float = 0.0,
) -> Image.Image:
    """Rend le symbole à `taille` pixels. `marge` en fraction de la taille."""
    grand = taille * SUPER
    image = Image.new("RGBA", (grand, grand), TRANSPARENT)
    dessin = ImageDraw.Draw(image)
    if fond != TRANSPARENT:
        dessin.rounded_rectangle(
            [0, 0, grand - 1, grand - 1], radius=rayon_fond * grand, fill=fond
        )
    interieur = grand * (1 - 2 * marge)
    echelle = interieur / 120
    decalage = grand * marge
    for x, y, largeur, hauteur in barres:
        gauche = decalage + x * echelle
        haut = decalage + y * echelle
        dessin.rounded_rectangle(
            [gauche, haut, gauche + largeur * echelle, haut + hauteur * echelle],
            radius=largeur * echelle / 2,
            fill=encre,
        )
    return image.resize((taille, taille), Image.LANCZOS)


def ecrire(image: Image.Image, nom: str) -> None:
    chemin = SORTIE / nom
    image.save(chemin)
    print(f"  {nom}")


def main() -> int:
    SORTIE.mkdir(parents=True, exist_ok=True)
    print(f"Export dans {SORTIE.relative_to(ROOT)} :")

    for taille in (16, 24, 32, 48, 64, 128, 256, 512, 1024):
        ecrire(dessiner(taille, BARRES, VERT), f"symbole-vert-{taille}.png")
    for taille in (16, 24, 32, 48, 64, 128, 256, 512):
        ecrire(dessiner(taille, BARRES, CREME), f"symbole-creme-{taille}.png")
    for taille in (32, 64, 128, 256, 512):
        ecrire(dessiner(taille, BARRES, ENCRE), f"symbole-encre-{taille}.png")

    # Icône d'application : symbole crème sur vert, coins arrondis, marge d'air.
    for taille in (16, 32, 64, 128, 180, 192, 256, 512, 1024):
        ecrire(
            dessiner(
                taille, BARRES, CREME, fond=VERT_FONCE, rayon_fond=0.222, marge=0.16
            ),
            f"icone-app-{taille}.png",
        )

    # Favicon : trois barres, lisibles là où cinq se referment.
    for taille in (16, 32, 48, 64):
        ecrire(
            dessiner(taille, TROIS, CREME, fond=VERT, rayon_fond=0.22, marge=0.12),
            f"favicon-{taille}.png",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
