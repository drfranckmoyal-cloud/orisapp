"""Photos HEIC de l'iPhone : imprimables et affichables, l'original intact."""

from __future__ import annotations

import io
from typing import Any

from PIL import Image
from pillow_heif import from_pillow  # type: ignore[attr-defined]

from oris_api.services.images import en_jpeg
from tests.conftest import documents_by_type
from tests.test_deliveries_and_deletion import consultation_traitee
from tests.test_document_figures import deposer


def heic(largeur: int = 120, hauteur: int = 80) -> bytes:
    tampon = io.BytesIO()
    from_pillow(Image.new("RGB", (largeur, hauteur), (180, 90, 60))).save(tampon, quality=80)
    return tampon.getvalue()


def test_a_heic_photo_becomes_a_jpeg_of_the_same_size() -> None:
    sortie = en_jpeg(heic())
    with Image.open(io.BytesIO(sortie)) as image:
        assert image.format == "JPEG" and image.size == (120, 80)


def test_a_heic_attachment_is_previewed_as_jpeg_and_kept_as_heic(api: Any) -> None:
    encounter = consultation_traitee(api)
    piece = deposer(api, encounter["patient"]["id"], "IMG_0001.HEIC", heic())
    apercu = api.get(f"/patients/attachments/{piece}/apercu")
    assert apercu.status_code == 200
    assert apercu.headers["content-type"] == "image/jpeg"
    original = api.get(f"/patients/attachments/{piece}/contenu")
    assert original.headers["content-type"] == "image/heic"


def test_a_heic_photo_can_be_placed_in_a_document_and_printed(api: Any) -> None:
    encounter = consultation_traitee(api)
    note = documents_by_type(api, encounter["id"])["consultation_note"]
    piece = deposer(api, encounter["patient"]["id"], "IMG_0002.HEIC", heic())
    posee = api.put(
        f"/documents/{note['id']}/figures",
        json={"figures": [{"attachment_id": piece, "caption": "Vue de face"}]},
    )
    assert posee.status_code == 200, posee.text
    pdf = api.get(f"/documents/{note['id']}/export", params={"format": "pdf"})
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
