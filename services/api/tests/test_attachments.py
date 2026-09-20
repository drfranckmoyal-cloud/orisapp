"""Pièces jointes du patient (spec §55).

Ce que ces tests tiennent :
- un format inconnu est refusé, pas rangé « au cas où » ;
- le même fichier importé deux fois ne se range qu'une ;
- le fichier ressort exactement tel qu'il est entré ;
- une pièce jointe n'entre **jamais** dans le dossier clinique.
"""

from __future__ import annotations

from typing import Any

from tests.conftest import clinical_object, run_synthetic

# Un PNG minuscule mais valide, et un STL en ASCII : deux natures différentes.
PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
    "890000000a49444154789c6360000002000100ffff03000006000557bfabd400"
    "00000049454e44ae426082"
)
STL = b"solid maxillaire\nfacet normal 0 0 1\nendfacet\nendsolid maxillaire\n"


def nouveau_patient(api: Any) -> str:
    reponse = api.post("/patients", json={"first_name": "Test", "last_name": "Pièces"})
    return str(reponse.json()["id"])


def test_a_photo_and_a_scan_are_imported_and_come_back_untouched(api: Any) -> None:
    pid = nouveau_patient(api)
    reponse = api.post(
        f"/patients/{pid}/attachments",
        files=[
            ("files", ("sourire.png", PNG, "image/png")),
            ("files", ("maxillaire.stl", STL, "model/stl")),
        ],
    )
    assert reponse.status_code == 201, reponse.text
    natures = {p["kind"]: p for p in reponse.json()}
    assert set(natures) == {"photo", "empreinte"}
    assert (
        natures["photo"]["media_type"] == "image/jpeg"
        or natures["photo"]["media_type"] == "image/png"
    )
    assert natures["empreinte"]["byte_size"] == len(STL)

    listees = api.get(f"/patients/{pid}/attachments").json()
    assert {p["filename"] for p in listees} == {"sourire.png", "maxillaire.stl"}

    # Le fichier ressort tel quel : rien n'est recompressé, rien n'est converti.
    piece = next(p for p in listees if p["filename"] == "maxillaire.stl")
    contenu = api.get(f"/patients/attachments/{piece['id']}/contenu")
    assert contenu.status_code == 200
    assert contenu.content == STL


def test_an_unknown_format_is_refused_rather_than_kept(api: Any) -> None:
    """Un fichier qu'on ne saura pas rouvrir n'a pas sa place au dossier."""
    pid = nouveau_patient(api)
    refuse = api.post(
        f"/patients/{pid}/attachments",
        files=[("files", ("notes.exe", b"MZ\x00\x00", "application/octet-stream"))],
    )
    assert refuse.status_code == 422
    assert refuse.json()["code"] == "UNSUPPORTED_ATTACHMENT_FORMAT"
    assert api.get(f"/patients/{pid}/attachments").json() == []


def test_the_same_file_twice_is_stored_once(api: Any) -> None:
    pid = nouveau_patient(api)
    api.post(f"/patients/{pid}/attachments", files=[("files", ("a.png", PNG, "image/png"))])
    api.post(f"/patients/{pid}/attachments", files=[("files", ("copie.png", PNG, "image/png"))])
    listees = api.get(f"/patients/{pid}/attachments").json()
    assert len(listees) == 1
    assert listees[0]["filename"] == "a.png"


def test_an_attachment_can_be_removed(api: Any) -> None:
    pid = nouveau_patient(api)
    piece = api.post(
        f"/patients/{pid}/attachments", files=[("files", ("a.png", PNG, "image/png"))]
    ).json()[0]
    assert api.delete(f"/patients/attachments/{piece['id']}").status_code == 204
    assert api.get(f"/patients/{pid}/attachments").json() == []
    assert api.get(f"/patients/attachments/{piece['id']}/contenu").status_code == 404


def test_an_attachment_never_enters_the_clinical_record(api: Any) -> None:
    """Oris ne lit pas les pièces jointes : elles accompagnent, elles ne nourrissent pas."""
    encounter = run_synthetic(api, "ORIS-SYN-001")
    pid = encounter["patient"]["id"]
    api.post(
        f"/patients/{pid}/attachments",
        files=[("files", ("radio-panoramique-26.png", PNG, "image/png"))],
    )
    objet = clinical_object(api, encounter["id"])
    assert all(fait["source_type"] != "attachment" for fait in objet["facts"])
    assert all("radio-panoramique" not in str(fait.get("value", "")) for fait in objet["facts"])
    documents = api.get(f"/encounters/{encounter['id']}/documents").json()
    assert all("radio-panoramique" not in document["content"] for document in documents)


def test_a_dangerous_filename_cannot_escape_its_folder(api: Any) -> None:
    pid = nouveau_patient(api)
    piece = api.post(
        f"/patients/{pid}/attachments",
        files=[("files", ("../../etc/passwd.png", PNG, "image/png"))],
    ).json()[0]
    assert "/" not in piece["filename"]
    assert ".." not in piece["filename"]
