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


def affichable(contenu: bytes, media_type: str) -> tuple[bytes, str]:
    """Le contenu tel qu'un navigateur ou un PDF sait l'afficher, et son type."""
    if media_type in HEIC:
        return en_jpeg(contenu), "image/jpeg"
    return contenu, media_type
