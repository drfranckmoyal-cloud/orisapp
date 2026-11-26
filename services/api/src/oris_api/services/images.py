"""Photos : les rendre imprimables et affichables partout.

L'iPhone enregistre ses photos en HEIC, que ni un PDF ni la plupart des navigateurs ne
savent afficher. Oris les convertit en JPEG à la volée — l'original reste tel quel dans
les pièces jointes. Au passage, l'orientation notée par l'appareil (EXIF) est appliquée :
une photo prise en portrait ne sort pas couchée.
"""

from __future__ import annotations

import io

from PIL import Image, ImageOps
from pillow_heif import register_heif_opener  # type: ignore[attr-defined]

register_heif_opener()

HEIC = frozenset({"image/heic", "image/heif"})
#: Ce qu'Oris sait poser dans un PDF, directement ou après conversion.
IMPRIMABLES = frozenset({"image/jpeg", "image/png", "image/webp"}) | HEIC


def en_jpeg(contenu: bytes, qualite: int = 90) -> bytes:
    """Une image quelconque (HEIC compris), redressée, en JPEG."""
    with Image.open(io.BytesIO(contenu)) as image:
        redressee = ImageOps.exif_transpose(image) or image
        tampon = io.BytesIO()
        redressee.convert("RGB").save(tampon, format="JPEG", quality=qualite)
        return tampon.getvalue()


#: Côté le plus long d'une photo posée dans un PDF. Pleine largeur d'une page A4 (18 cm)
#: à 280 points par pouce : la photo reste nette à l'impression et à l'écran, sans peser
#: les 10 à 20 Mo d'un original (le 26/11/2026, un compte rendu de 64 Mo a été refusé
#: par Gmail, limité à 25 Mo).
COTE_IMPRESSION = 2000


def pour_impression(contenu: bytes, cote: int = COTE_IMPRESSION, qualite: int = 85) -> bytes:
    """Une photo prête pour le PDF : redressée, ramenée à `cote` pixels au plus, en JPEG."""
    with Image.open(io.BytesIO(contenu)) as image:
        redressee = ImageOps.exif_transpose(image) or image
        redressee = redressee.convert("RGB")
        redressee.thumbnail((cote, cote), Image.Resampling.LANCZOS)
        tampon = io.BytesIO()
        redressee.save(tampon, format="JPEG", quality=qualite, optimize=True)
        return tampon.getvalue()


def affichable(contenu: bytes, media_type: str) -> tuple[bytes, str]:
    """Le contenu tel qu'un navigateur ou un PDF sait l'afficher, et son type."""
    if media_type in HEIC:
        return en_jpeg(contenu), "image/jpeg"
    return contenu, media_type
