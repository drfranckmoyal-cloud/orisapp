"""Le dialogue de correction : comprendre d'abord, appliquer sur confirmation.

Franck, le 10/11/2026 : « j'aimerais pouvoir proposer des corrections dans une boîte de
dialogue IA ». Ces essais tiennent ce qui ne doit pas bouger : Claude ne change rien
lui-même, une demande de forme ne touche jamais un fait, une réponse bancale redevient
une question, et le service d'IA en panne se dit en clair.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx
import pytest

from oris_api.domain.preferences import ajouter_consigne
from oris_api.llm.assistant import AssistantCorrections, AssistantIndisponible, lire
from tests.test_redaction_consultation import dictee


def assistant(reponse: dict[str, Any], statut: int = 200) -> tuple[AssistantCorrections, list[Any]]:
    envoyes: list[Any] = []

    def repondre(request: httpx.Request) -> httpx.Response:
        corps = json.loads(request.content)
        envoyes.append(corps)
        if statut != 200:
            return httpx.Response(statut, json={"error": {"message": "non"}})
        outil = corps["tool_choice"]["name"]
        return httpx.Response(
            200, json={"content": [{"type": "tool_use", "name": outil, "input": reponse}]}
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(repondre))
    return AssistantCorrections("cle", "modele", client), envoyes


def test_une_demande_de_forme_devient_une_consigne_et_aucune_operation() -> None:
    obj = dictee()
    lecture = lire(
        {
            "nature": "redaction",
            "resume": "J'allège les attributions.",
            "consigne": "Attribuer les propos du patient une seule fois par paragraphe",
            # Même si le modèle glissait une opération, une demande de forme n'en porte pas.
            "operations": [{"operation": "remove_fact", "fact_id": obj.facts[0].fact_id}],
        },
        obj,
    )
    assert lecture.nature == "redaction"
    assert lecture.operations == []
    assert lecture.consigne.startswith("Attribuer")


def test_une_operation_sur_un_fait_inconnu_redevient_une_question() -> None:
    lecture = lire(
        {
            "nature": "dossier",
            "resume": "Je retire ce fait.",
            "operations": [{"operation": "remove_fact", "fact_id": "f-qui-n-existe-pas"}],
        },
        dictee(),
    )
    assert lecture.nature == "incompris"
    assert lecture.operations == []


def test_une_operation_mal_formee_redevient_une_question() -> None:
    lecture = lire(
        {
            "nature": "dossier",
            "resume": "…",
            "operations": [{"operation": "replace_tooth", "from_tooth": "99", "to_tooth": "27"}],
        },
        dictee(),
    )
    assert lecture.nature == "incompris"


def test_reordonner_le_plan_ne_passe_pas_par_le_dialogue() -> None:
    lecture = lire(
        {
            "nature": "dossier",
            "resume": "…",
            "operations": [{"operation": "reorder_plan_items", "item_ids": ["a"]}],
        },
        dictee(),
    )
    assert lecture.nature == "incompris"


def test_la_civilite_exige_une_valeur_connue() -> None:
    assert (
        lire({"nature": "civilite", "resume": "…", "civilite": "madame"}, dictee()).civilite
        == "madame"
    )
    assert lire({"nature": "civilite", "resume": "…"}, dictee()).nature == "incompris"


def test_claude_voit_les_faits_jamais_le_nom_du_patient() -> None:
    claude, envoyes = assistant({"nature": "incompris", "resume": "?", "question": "?"})
    asyncio.run(claude.comprendre("plus court", dictee(), "madame"))
    contenu = json.loads(envoyes[0]["messages"][0]["content"])
    assert set(contenu) == {"demande", "civilite_connue", "dossier"}
    assert set(contenu["dossier"]) == {"faits", "plan"}
    assert "patient_id" not in envoyes[0]["messages"][0]["content"]


def test_une_cle_refusee_se_dit_en_clair() -> None:
    claude, _ = assistant({}, statut=401)
    with pytest.raises(AssistantIndisponible) as panne:
        asyncio.run(claude.comprendre("plus court", dictee()))
    assert panne.value.code == "ANTHROPIC_AUTH"


def test_la_relecture_borne_et_nettoie_les_propositions() -> None:
    claude, _ = assistant(
        {
            "propositions": [
                {"titre": f"Idée {i}", "detail": "ici", "consigne": "Faire court"} for i in range(9)
            ]
            + [{"titre": "", "detail": "", "consigne": ""}]
        }
    )
    propositions = asyncio.run(
        claude.relire("consultation_note", [{"titre": "A", "texte": "b"}], [])
    )
    assert len(propositions) == 5
    assert all(p.consigne == "Faire court" for p in propositions)


def test_une_consigne_ne_se_range_pas_deux_fois() -> None:
    assert ajouter_consigne(["Faire court"], "  faire   COURT ") == ["faire COURT"]
    assert len(ajouter_consigne([f"c {i}" for i in range(20)], "nouvelle")) == 20


# --- Les routes -------------------------------------------------------------------------


def consultation(api: Any) -> tuple[str, int]:
    """Une consultation fictive traitée : rien n'en sort, le dialogue reste aux règles."""
    cas = api.get("/synthetic-cases").json()[0]["case_id"]
    patient = api.post("/patients", json={"first_name": "Anne", "last_name": "TEST"}).json()
    rencontre = api.post(
        "/encounters", json={"patient_id": patient["id"], "synthetic_case_id": cas}
    ).json()
    api.post(f"/encounters/{rencontre['id']}/start", json={"patient_informed": True})
    fini = api.post(f"/encounters/{rencontre['id']}/finish")
    assert fini.status_code == 200, fini.text
    return rencontre["id"], fini.json()["object_version"]


def test_sans_ia_une_tournure_connue_est_comprise_par_les_regles(api: Any) -> None:
    identifiant, _ = consultation(api)
    reponse = api.post(f"/encounters/{identifiant}/assistant", json={"demande": "plus court"})
    assert reponse.status_code == 200, reponse.text
    lecture = reponse.json()
    assert lecture["source"] == "regles"
    assert lecture["nature"] == "redaction"
    assert lecture["operations"] == []


def test_une_consigne_appliquee_est_rangee_et_peut_etre_retenue(api: Any) -> None:
    identifiant, _ = consultation(api)
    applique = api.post(
        f"/encounters/{identifiant}/assistant/appliquer",
        json={"nature": "redaction", "consignes": ["Faire des phrases courtes"], "retenir": True},
    )
    assert applique.status_code == 200, applique.text
    assert applique.json()["applique"] is True
    consignes = api.get(f"/encounters/{identifiant}/consignes").json()
    assert consignes == {
        "consultation": ["Faire des phrases courtes"],
        "praticien": ["Faire des phrases courtes"],
    }
    assert api.get("/me/preferences").json()["consignes"] == ["Faire des phrases courtes"]

    retire = api.put(f"/encounters/{identifiant}/consignes", json={"consultation": []})
    assert retire.json()["consultation"] == []
    assert retire.json()["praticien"] == ["Faire des phrases courtes"]


def test_la_civilite_dite_dans_le_dialogue_va_dans_la_fiche(api: Any) -> None:
    identifiant, _ = consultation(api)
    applique = api.post(
        f"/encounters/{identifiant}/assistant/appliquer",
        json={"nature": "civilite", "civilite": "madame"},
    )
    assert applique.status_code == 200, applique.text
    rencontre = api.get(f"/encounters/{identifiant}").json()
    assert api.get(f"/patients/{rencontre['patient']['id']}").json()["civility"] == "madame"


def test_une_correction_du_dossier_exige_la_version_attendue(api: Any) -> None:
    identifiant, _ = consultation(api)
    refus = api.post(
        f"/encounters/{identifiant}/assistant/appliquer",
        json={
            "nature": "dossier",
            "operations": [{"operation": "replace_tooth", "from_tooth": "26", "to_tooth": "27"}],
        },
    )
    assert refus.status_code == 409
    assert refus.json()["code"] == "OBJECT_VERSION_REQUIRED"


def test_la_relecture_dit_quand_l_ia_n_est_pas_la(api: Any) -> None:
    identifiant, _ = consultation(api)
    documents = api.get(f"/encounters/{identifiant}/documents").json()
    note = next(d for d in documents if d["document_type"] == "consultation_note")
    reponse = api.post(f"/documents/{note['id']}/relecture")
    assert reponse.status_code == 503
    assert reponse.json()["code"] == "ASSISTANT_UNAVAILABLE"


def test_dix_frappes_ne_font_pas_dix_versions(api: Any) -> None:
    identifiant, _ = consultation(api)
    documents = api.get(f"/encounters/{identifiant}/documents").json()
    note = next(d for d in documents if d["document_type"] == "consultation_note")
    premiere = api.post(f"/documents/{note['id']}/text", json={"content": "Texte du praticien."})
    assert premiere.status_code == 200, premiere.text
    version = premiere.json()["version"]
    seconde = api.post(
        f"/documents/{note['id']}/text", json={"content": "Texte du praticien, repris."}
    )
    assert seconde.status_code == 200, seconde.text
    assert seconde.json()["version"] == version
    assert "repris" in seconde.json()["content"]
