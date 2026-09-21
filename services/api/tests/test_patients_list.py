"""La liste des patients : ce qu'elle sait dire sans ouvrir un dossier."""

from __future__ import annotations

from typing import Any


def test_the_patient_list_counts_the_consultations_without_a_query_per_row(api: Any) -> None:
    """La liste dit combien de comptes rendus, le dernier, et ce qui attend d'être relu."""
    avec = api.post("/patients", json={"first_name": "Avec", "last_name": "Consultations"}).json()
    sans = api.post("/patients", json={"first_name": "Sans", "last_name": "Rien"}).json()
    for _ in range(3):
        api.post("/encounters", json={"patient_id": avec["id"]})

    liste = {p["last_name"]: p for p in api.get("/patients").json()}
    assert liste["Consultations"]["consultations"] == 3
    assert liste["Consultations"]["derniere_consultation"] is not None
    assert liste["Consultations"]["a_relire"] == 0
    # Un patient sans consultation dit zéro, il ne disparaît pas de la liste.
    assert liste["Rien"]["consultations"] == 0
    assert liste["Rien"]["derniere_consultation"] is None
    assert sans["id"] in {p["id"] for p in api.get("/patients").json()}
