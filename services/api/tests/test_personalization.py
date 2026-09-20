"""Personnalisation : dictionnaire, préférences, suggestions — et retour en arrière."""

from __future__ import annotations

from typing import Any

from tests.conftest import documents_by_type, run_synthetic


def test_preferences_start_at_oris_defaults_and_can_be_changed(api: Any) -> None:
    assert api.get("/me/preferences").json() == {
        "document_length": "standard",
        "terminology": {},
    }
    updated = api.patch(
        "/me/preferences",
        json={"document_length": "concise", "terminology": {"extraction": "avulsion"}},
    ).json()
    assert updated["document_length"] == "concise"
    assert updated["terminology"]["extraction"] == "avulsion"
    # Retour au défaut : rien n'est définitif.
    assert (
        api.patch("/me/preferences", json={"document_length": "standard"}).json()["document_length"]
        == "standard"
    )


def test_preferred_word_is_used_without_touching_the_facts(api: Any) -> None:
    api.patch(
        "/me/preferences", json={"terminology": {"cold_sensitivity": "sensibilité au froid vif"}}
    )
    eid = run_synthetic(api, "ORIS-SYN-092")["id"]
    note = documents_by_type(api, eid)["consultation_note"]
    assert "sensibilité au froid vif" in note["content"]
    object_facts = api.get(f"/encounters/{eid}/clinical-object").json()["clinical_object"]["facts"]
    # Le fait, lui, n'a pas bougé : la préférence est une affaire de forme.
    assert any(fact["concept"] == "cold_sensitivity" for fact in object_facts)
    assert all(fact["value"] != "sensibilité au froid vif" for fact in object_facts)


def test_concise_mode_drops_only_what_repeats_the_section(api: Any) -> None:
    eid = run_synthetic(api, "ORIS-SYN-092")["id"]
    standard = documents_by_type(api, eid)["consultation_note"]["content"]
    assert "Rapporté par le patient : sensibilité au froid" in standard

    api.patch("/me/preferences", json={"document_length": "concise"})
    api.post(f"/encounters/{eid}/documents/generate")
    concise = documents_by_type(api, eid)["consultation_note"]["content"]
    assert "Rapporté par le patient : sensibilité au froid" not in concise
    assert "Sensibilité au froid" in concise
    # Une nuance n'est jamais supprimée : l'absence reste écrite.
    assert "absence de douleur nocturne" in concise.lower()


def test_a_glossary_term_is_added_then_disabled(api: Any) -> None:
    created = api.post(
        "/glossary",
        json={
            "canonical": "G-ænial A'CHORD",
            "aliases": ["genial accord", "genial a chord"],
            "category": "material",
        },
    )
    assert created.status_code == 201
    term = created.json()
    assert term["status"] == "active" and term["origin"] == "manual"

    disabled = api.patch(f"/glossary/{term['id']}", json={"status": "disabled"}).json()
    assert disabled["status"] == "disabled"
    assert [t["status"] for t in api.get("/glossary").json()] == ["disabled"]


def test_the_practitioner_dictionary_reaches_the_providers(api: Any) -> None:
    """Un terme actif est soufflé à la transcription et à l'extraction ; désactivé, non."""
    from dataclasses import replace
    from typing import ClassVar

    from oris_api.main import app
    from oris_api.providers.base import ProviderInfo

    class SpyExtraction:
        info = ProviderInfo(name="spy", version="0", capabilities=[])
        seen: ClassVar[list[list[str]]] = []

        def __init__(self, inner: Any) -> None:
            self.inner = inner

        async def extract(self, segments: Any, glossary: Any) -> Any:
            SpyExtraction.seen.append([hint.canonical for hint in glossary])
            return await self.inner.extract(segments, glossary)

    api.post("/glossary", json={"canonical": "Variolink Esthetic", "aliases": ["variolink"]})
    original = app.state.providers
    app.state.providers = replace(
        original, clinical_extraction=SpyExtraction(original.clinical_extraction)
    )
    try:
        run_synthetic(api, "ORIS-SYN-092")
    finally:
        app.state.providers = original
    assert SpyExtraction.seen and "Variolink Esthetic" in SpyExtraction.seen[-1]


def test_repeated_style_requests_become_a_suggestion_not_a_rule(api: Any) -> None:
    eid = run_synthetic(api, "ORIS-SYN-092")["id"]
    assert api.get("/me/learning/suggestions").json() == []

    for _ in range(2):
        api.post(
            f"/encounters/{eid}/corrections/text",
            json={
                "command": "fais le compte rendu plus court",
                "apply": True,
                "expected_object_version": 1,
            },
        )
    suggestions = api.get("/me/learning/suggestions").json()
    assert len(suggestions) == 1
    assert suggestions[0]["kind"] == "preference"
    assert suggestions[0]["occurrences"] == 2
    assert suggestions[0]["payload"] == {"field": "document_length", "value": "concise"}
    # Proposé seulement : la préférence n'a pas changé toute seule.
    assert api.get("/me/preferences").json()["document_length"] == "standard"

    api.patch("/me/preferences", json={"document_length": "concise"})
    assert api.get("/me/learning/suggestions").json() == []


def test_the_practice_identity_is_saved_and_printed_on_documents(api: Any) -> None:
    """Ce que le praticien saisit dans Paramètres s'imprime en tête de ses documents (§78)."""
    depart = api.get("/me/cabinet").json()
    assert depart["name"] == "Cabinet de démonstration"
    assert depart["practitioner_name"] == "Franck Moyal"

    enregistre = api.patch(
        "/me/cabinet",
        json={
            "name": "Cabinet des Lilas",
            "address": "12 rue des Lilas, 75000 Paris",
            "phone": "01 23 45 67 89",
            "legal": "RPPS 10101010101",
            "practitioner_title": "Dr",
        },
    ).json()
    assert enregistre["name"] == "Cabinet des Lilas"

    eid = run_synthetic(api, "ORIS-SYN-092")["id"]
    note = documents_by_type(api, eid)["consultation_note"]
    texte = api.get(f"/documents/{note['id']}/export", params={"format": "structured"}).text
    assert "Cabinet des Lilas" in texte

    pdf = api.get(f"/documents/{note['id']}/export", params={"format": "pdf"})
    assert pdf.content.startswith(b"%PDF")


def test_an_empty_practice_identity_falls_back_without_breaking(api: Any) -> None:
    api.patch("/me/cabinet", json={"address": ""})
    eid = run_synthetic(api, "ORIS-SYN-092")["id"]
    note = documents_by_type(api, eid)["consultation_note"]
    assert api.get(f"/documents/{note['id']}/export", params={"format": "pdf"}).status_code == 200
