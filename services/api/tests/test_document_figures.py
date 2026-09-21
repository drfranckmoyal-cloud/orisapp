"""« Documentation clinique » : les photos choisies pour un document.

Ce que ces tests tiennent :
- le document cite des pièces jointes du patient, dans l'ordre choisi, légendées ;
- une pièce d'un autre patient, ou non imprimable (HEIC, STL), est refusée ;
- le PDF gagne une page, placée après le texte ;
- supprimer la pièce jointe la retire du document.
"""

from __future__ import annotations

import io
from typing import Any

from reportlab.lib.utils import ImageReader  # noqa: F401 - Pillow disponible

from tests.conftest import documents_by_type
from tests.test_deliveries_and_deletion import consultation_traitee


def photo(teinte: int = 160) -> bytes:
    """Deux photos identiques ne font qu'une pièce jointe : la teinte les distingue."""
    from PIL import Image

    tampon = io.BytesIO()
    Image.new("RGB", (400, 300), (200, 180, teinte)).save(tampon, format="JPEG")
    return tampon.getvalue()


def deposer(api: Any, patient_id: str, nom: str, contenu: bytes) -> str:
    reponse = api.post(f"/patients/{patient_id}/attachments", files={"files": (nom, contenu)})
    assert reponse.status_code in (200, 201), reponse.text
    return str(reponse.json()[0]["id"])


def test_figures_are_set_in_order_with_their_captions_and_printed(api: Any) -> None:
    encounter = consultation_traitee(api)
    patient_id = encounter["patient"]["id"]
    note = documents_by_type(api, encounter["id"])["consultation_note"]
    avant = api.get(f"/documents/{note['id']}/export", params={"format": "pdf"}).content

    a = deposer(api, patient_id, "face.jpg", photo())
    b = deposer(api, patient_id, "sourire.jpg", photo(90))
    posees = api.put(
        f"/documents/{note['id']}/figures",
        json={
            "figures": [
                {"attachment_id": b, "caption": "Sourire de face"},
                {"attachment_id": a, "caption": "Vue occlusale"},
            ]
        },
    )
    assert posees.status_code == 200, posees.text
    assert [(f["attachment_id"], f["caption"]) for f in posees.json()] == [
        (b, "Sourire de face"),
        (a, "Vue occlusale"),
    ]

    apres = api.get(f"/documents/{note['id']}/export", params={"format": "pdf"}).content
    assert apres.count(b"/Type /Page\n") == avant.count(b"/Type /Page\n") + 1


def test_a_file_that_cannot_be_printed_is_refused(api: Any) -> None:
    encounter = consultation_traitee(api)
    note = documents_by_type(api, encounter["id"])["consultation_note"]
    stl = deposer(api, encounter["patient"]["id"], "arcade.stl", b"solid x\nendsolid x\n")
    refus = api.put(f"/documents/{note['id']}/figures", json={"figures": [{"attachment_id": stl}]})
    assert refus.status_code == 422
    assert refus.json()["code"] == "FIGURE_NOT_PRINTABLE"


def test_another_patients_photo_is_refused(api: Any) -> None:
    encounter = consultation_traitee(api)
    note = documents_by_type(api, encounter["id"])["consultation_note"]
    autre = api.post("/patients", json={"first_name": "Autre", "last_name": "Patient"}).json()
    etrangere = deposer(api, autre["id"], "face.jpg", photo())
    refus = api.put(
        f"/documents/{note['id']}/figures", json={"figures": [{"attachment_id": etrangere}]}
    )
    assert refus.status_code == 404


def test_removing_the_attachment_removes_the_figure(api: Any) -> None:
    encounter = consultation_traitee(api)
    note = documents_by_type(api, encounter["id"])["consultation_note"]
    a = deposer(api, encounter["patient"]["id"], "face.jpg", photo())
    api.put(f"/documents/{note['id']}/figures", json={"figures": [{"attachment_id": a}]})
    api.delete(f"/patients/attachments/{a}")
    assert api.get(f"/documents/{note['id']}/figures").json() == []
