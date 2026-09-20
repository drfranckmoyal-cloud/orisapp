#!/usr/bin/env python3
"""Exporte la marque Oris en PNG, à toutes les tailles utiles.

Le symbole n'est fait que de rectangles arrondis : on le dessine directement, à
quatre fois la taille voulue, puis on réduit. Le rendu est net à 16 px sans
dépendre d'un moteur SVG installé sur la machine.

Le mot « Oris » est composé en Fraunces 600, taille optique 48, WONK désactivé —
les mêmes réglages que la version vectorisée des SVG (`scripts/vectoriser_nom.py`).
La police est dans le dépôt, sous licence SIL OFL.

Usage :
  python3 scripts/export_marque.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
SORTIE = ROOT / "design" / "marque" / "png"
POLICE = ROOT / "design" / "marque" / "polices" / "Fraunces.ttf"
# Ordre des axes de Fraunces, tel que la police les déclare.
AXES = [48, 600, 0, 0]  # opsz, wght, SOFT, WONK

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


def police(hauteur_capitale: float) -> ImageFont.FreeTypeFont:
    """Fraunces réglée pour que la hauteur de capitale tombe juste.

    On cherche le corps par dichotomie plutôt que de deviner : la hauteur de
    capitale d'une police variable ne se déduit pas du corps.
    """
    bas, haut = 4, 4000
    while bas < haut:
        milieu = (bas + haut + 1) // 2
        essai = ImageFont.truetype(POLICE, milieu)
        essai.set_variation_by_axes(AXES)
        _, y0, _, y1 = essai.getbbox("O")
        if (y1 - y0) <= hauteur_capitale:
            bas = milieu
        else:
            haut = milieu - 1
    choisie = ImageFont.truetype(POLICE, bas)
    choisie.set_variation_by_axes(AXES)
    return choisie


def verrouillage(hauteur: int, encre, vertical: bool = False) -> Image.Image:
    """Symbole + nom, aux proportions des SVG : le mot fait 80 % des barres."""
    grand = hauteur * SUPER
    echelle = grand / 120
    fonte = police(76 * 0.80 * echelle)
    x0, y0, x1, y1 = fonte.getbbox("Oris")
    largeur_mot, capitale = x1 - x0, 76 * 0.80 * echelle

    if vertical:
        ecart = 20 * echelle
        largeur = max(grand, largeur_mot)
        total_h = grand + ecart + (y1 - y0)
        image = Image.new("RGBA", (round(largeur), round(total_h)), TRANSPARENT)
        symbole = dessiner(hauteur, BARRES, encre)
        image.alpha_composite(
            symbole.resize((grand, grand), Image.LANCZOS),
            (round((largeur - grand) / 2), 0),
        )
        ImageDraw.Draw(image).text(
            (round((largeur - largeur_mot) / 2 - x0), round(grand + ecart)),
            "Oris",
            font=fonte,
            fill=encre,
            anchor="la",
        )
        cible = (round(largeur / SUPER), round(total_h / SUPER))
    else:
        ecart = 26 * echelle
        largeur = grand + ecart + largeur_mot
        image = Image.new("RGBA", (round(largeur), grand), TRANSPARENT)
        image.alpha_composite(
            dessiner(hauteur, BARRES, encre).resize((grand, grand), Image.LANCZOS),
            (0, 0),
        )
        ImageDraw.Draw(image).text(
            (round(grand + ecart - x0), round(grand / 2 + capitale / 2)),
            "Oris",
            font=fonte,
            fill=encre,
            anchor="ls",
        )
        cible = (round(largeur / SUPER), hauteur)
    return image.resize(cible, Image.LANCZOS)


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

    # Verrouillages : le nom est composé, plus jamais tapé à la volée.
    for hauteur in (48, 96, 192, 384):
        ecrire(verrouillage(hauteur, VERT), f"logo-horizontal-{hauteur}.png")
        ecrire(verrouillage(hauteur, CREME), f"logo-creme-{hauteur}.png")
        ecrire(verrouillage(hauteur, ENCRE), f"logo-monochrome-{hauteur}.png")
    for hauteur in (96, 192, 384):
        ecrire(
            verrouillage(hauteur, VERT, vertical=True), f"logo-vertical-{hauteur}.png"
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
