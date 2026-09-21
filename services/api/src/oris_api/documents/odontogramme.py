"""Schéma dentaire des deux arcades, vues d'en haut, pour le plan de traitement.

Chaque dent a la largeur et l'épaisseur moyennes de son type (incisive, canine,
prémolaire, molaire) ; les arcades suivent une courbe en U. Les dents d'une étape sont
teintées de la couleur de l'étape et marquées d'une pastille par étape ; une dent
absente est dessinée en pointillé.

Coordonnées « écran » : l'axe vertical descend (le maxillaire en haut). La géométrie
est indépendante du support : le PDF (ReportLab) et l'écran (SVG, côté
web) en dessinent la même chose.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from itertools import pairwise

#: (largeur mésio-distale, épaisseur vestibulo-linguale) en mm, par rang dans le quadrant.
HAUT = {
    1: (8.5, 7.0),
    2: (6.6, 6.2),
    3: (7.6, 8.0),
    4: (7.0, 9.0),
    5: (6.6, 9.0),
    6: (10.2, 11.0),
    7: (9.2, 10.6),
    8: (8.6, 10.0),
}
BAS = {
    1: (5.4, 6.0),
    2: (5.9, 6.4),
    3: (6.9, 7.6),
    4: (7.0, 7.8),
    5: (7.1, 8.2),
    6: (11.0, 10.4),
    7: (10.4, 10.0),
    8: (10.0, 9.6),
}

#: Couleur de chaque étape : trait franc et teinte douce.
TEINTES: tuple[tuple[str, str], ...] = (
    ("#B8365A", "#F6DCE4"),
    ("#2F6FB0", "#DCE8F6"),
    ("#2E8A57", "#DAF0E3"),
    ("#B7791F", "#F7E9CF"),
    ("#6B4C9A", "#E7DEF3"),
    ("#0F7C8C", "#D4EEF1"),
)


def teinte(index: int) -> tuple[str, str]:
    return TEINTES[index % len(TEINTES)]


@dataclass(frozen=True)
class DentPlacee:
    numero: str
    x: float
    y: float
    angle: float  # degrés, rotation de la dent le long de l'arcade
    largeur: float
    epaisseur: float
    dehors: tuple[float, float]  # direction vers l'extérieur de l'arcade (unitaire)
    rang: int  # 1 incisive centrale … 8 dent de sagesse


def ordre(arcade: str) -> list[str]:
    """De la droite du patient (à gauche du lecteur) à sa gauche."""
    if arcade == "haut":
        return [f"1{i}" for i in range(8, 0, -1)] + [f"2{i}" for i in range(1, 9)]
    return [f"4{i}" for i in range(8, 0, -1)] + [f"3{i}" for i in range(1, 9)]


def placer(arcade: str, cx: float, cy: float, a: float, b: float) -> list[DentPlacee]:
    """Dents d'une arcade le long d'une demi-ellipse : ouverte vers le bas pour le
    maxillaire (incisives en haut), vers le haut pour la mandibule."""
    tailles = HAUT if arcade == "haut" else BAS
    signe = -1 if arcade == "haut" else 1
    debut, fin = math.pi - 0.02, 0.02
    pas = 400
    points = [
        (
            cx + a * math.cos(debut + (fin - debut) * i / pas),
            cy + signe * b * math.sin(debut + (fin - debut) * i / pas),
        )
        for i in range(pas + 1)
    ]
    cumul = [0.0]
    for (x0, y0), (x1, y1) in pairwise(points):
        cumul.append(cumul[-1] + math.hypot(x1 - x0, y1 - y0))
    longueur = cumul[-1]
    numeros = ordre(arcade)
    largeurs = [tailles[int(n[1])][0] for n in numeros]
    jeu = 0.9
    echelle = longueur / (sum(largeurs) + jeu * len(largeurs))

    placees: list[DentPlacee] = []
    parcouru = 0.0
    for numero, largeur in zip(numeros, largeurs, strict=True):
        milieu = (parcouru + (largeur + jeu) / 2) * echelle
        parcouru += largeur + jeu
        i = next(k for k, c in enumerate(cumul) if c >= milieu)
        i = min(max(i, 1), pas)
        (x0, y0), (x1, y1) = points[i - 1], points[i]
        x, y = points[i]
        tangente = math.degrees(math.atan2(y1 - y0, x1 - x0))
        dx, dy = x - cx, y - cy
        norme = math.hypot(dx, dy) or 1.0
        rang = int(numero[1])
        placees.append(
            DentPlacee(
                numero=numero,
                x=x,
                y=y,
                angle=tangente,
                largeur=tailles[rang][0] * echelle,
                epaisseur=tailles[rang][1] * echelle,
                dehors=(dx / norme, dy / norme),
                rang=rang,
            )
        )
    return placees
