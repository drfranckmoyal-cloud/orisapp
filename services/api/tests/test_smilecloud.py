"""SmileCloud de bout en bout, l'extension jouée par le test : liste des dossiers,
lien au patient, lecture des galeries, rapatriement — et ce qui ne passe pas se dit."""

from __future__ import annotations

from typing import Any

CASE = "0f3c2a1b-1111-4222-8333-944455556666"
AUTRE = "0f3c2a1b-9999-4222-8333-944455556666"
PHOTO = "a1b2c3d4-0000-4000-8000-000000000001"
VIDEO = "a1b2c3d4-0000-4000-8000-000000000002"
MAQUETTE = "a1b2c3d4-0000-4000-8000-000000000003"
# Un JPEG minuscule mais valide.
JPEG = bytes.fromhex(
    "ffd8ffe000104a46494600010100000100010000ffdb004300080606070605080707070909080a0c140d0c0b0b0c1912130f141d1a1f1e1d1a1c1c20242e2720222c231c1c2837292c30313434341f27393d38323c2e333432ffc0000b080001000101011100ffc4001f0000010501010101010100000000000000000102030405060708090a0bffc400b5100002010303020403050504040000017d01020300041105122131410613516107227114328191a1082342b1c11552d1f02433627282090a161718191a25262728292a3435363738393a434445464748494a535455565758595a636465666768696a737475767778797a838485868788898a92939495969798999aa2a3a4a5a6a7a8a9aab2b3b4b5b6b7b8b9bac2c3c4c5c6c7c8c9cad2d3d4d5d6d7d8d9dae1e2e3e4e5e6e7e8e9eaf1f2f3f4f5f6f7f8f9faffda0008010100003f00fbd3ffd9"
)


def test_a_patient_is_linked_then_gallery_files_come_home(api: Any) -> None:
    patient = api.post("/patients", json={"first_name": "Anne", "last_name": "ESSAI"}).json()
    pid = patient["id"]

    # Avant toute liste : Oris le dit, il ne devine pas.
    assert api.get(f"/patients/{pid}/smilecloud").json()["etat"] == "sans_liste"

    api.post(
        "/smilecloud/dossiers",
        json={
            "dossiers": [
                {"nom": "Anne Essai", "case_id": CASE},
                {"nom": "Annie Esai", "case_id": AUTRE},
            ]
        },
    )
    vue = api.get(f"/patients/{pid}/smilecloud").json()
    assert vue["etat"] == "trouve" and vue["candidats"][0]["case_id"] == CASE

    vue = api.put(f"/patients/{pid}/smilecloud", json={"case_id": CASE}).json()
    assert vue["etat"] == "relie" and vue["nom"] == "Anne Essai"

    # Demander les galeries : l'extension voit la demande, lit, livre.
    vue = api.post(f"/patients/{pid}/smilecloud/galeries").json()
    assert vue["lecture_en_cours"] is True
    demandes = api.get("/smilecloud/demandes").json()
    assert [(d["type"], d["case_id"]) for d in demandes] == [("galeries", CASE)]
    api.post(
        "/smilecloud/galeries",
        json={
            "case_id": CASE,
            "galeries": [
                {
                    "id": "g1",
                    "nom": "Photos initiales",
                    "date": "2026-09-01",
                    "fichiers": [
                        {"res_id": PHOTO, "nom": "face.jpg", "nature": "photo"},
                        {"res_id": VIDEO, "nom": "sourire.mp4", "nature": "video"},
                        {"res_id": MAQUETTE, "nom": "maquette.xyz", "nature": "autre"},
                    ],
                }
            ],
        },
    )
    vue = api.get(f"/patients/{pid}/smilecloud").json()
    assert vue["lecture_en_cours"] is False
    fichiers = {f["res_id"]: f for f in vue["galeries"][0]["fichiers"]}
    assert fichiers[VIDEO]["rapatriable"] is False

    # Rapatrier : la vidéo est écartée d'office et ne sera pas demandée à l'extension.
    vue = api.post(
        f"/patients/{pid}/smilecloud/recuperer", json={"fichiers": [PHOTO, VIDEO, MAQUETTE]}
    ).json()
    assert vue["recuperation"]["ecartes"] == [{"res_id": VIDEO, "raison": "video"}]
    demande = next(d for d in api.get("/smilecloud/demandes").json() if d["type"] == "fichiers")
    assert demande["fichiers"] == [PHOTO, MAQUETTE]

    recu = api.post(
        "/smilecloud/fichier",
        content=JPEG,
        headers={
            "Content-Type": "application/octet-stream",
            "X-Demande": demande["id"],
            "X-Res-Id": PHOTO,
            "X-Nom": "face.jpg",
        },
    ).json()
    assert recu["recu"] is True and recu["termine"] is False
    # Un format qu'Oris ne rouvre pas est refusé, et le refus se dit.
    refus = api.post(
        "/smilecloud/fichier",
        content=b"xyz",
        headers={
            "Content-Type": "application/octet-stream",
            "X-Demande": demande["id"],
            "X-Res-Id": MAQUETTE,
            "X-Nom": "maquette.xyz",
        },
    ).json()
    assert refus["recu"] is False and refus["termine"] is True

    vue = api.get(f"/patients/{pid}/smilecloud").json()
    assert vue["recuperation"]["recus"] == 1 and vue["recuperation"]["termine"] is True
    assert len(vue["recuperation"]["ecartes"]) == 2
    pieces = api.get(f"/patients/{pid}/attachments").json()
    assert [p["label"] for p in pieces] == ["SmileCloud · Photos initiales"]
    assert api.get("/smilecloud/demandes").json() == []


def test_a_doubtful_name_is_asked_not_guessed(api: Any) -> None:
    patient = api.post("/patients", json={"first_name": "Paul", "last_name": "MARTIN"}).json()
    api.post("/smilecloud/dossiers", json={"dossiers": [{"nom": "Paule Martin", "case_id": CASE}]})
    vue = api.get(f"/patients/{patient['id']}/smilecloud").json()
    assert vue["etat"] == "a_confirmer" and vue["candidats"][0]["pour_cent"] < 100


def test_gallery_reading_needs_a_link(api: Any) -> None:
    patient = api.post("/patients", json={"first_name": "Sans", "last_name": "LIEN"}).json()
    reponse = api.post(f"/patients/{patient['id']}/smilecloud/galeries")
    assert reponse.status_code == 422 and reponse.json()["code"] == "SMILECLOUD_NON_RELIE"
