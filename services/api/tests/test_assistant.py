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
from oris_api.llm.assistant import (
    AssistantCorrections,
    AssistantIndisponible,
    lire,
    normaliser,
)
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


def test_des_noms_de_champs_en_francais_sont_remis_au_contrat() -> None:
    """Franck, le 10/11/2026 : « il a compris mais pas réalisé ». Claude rendait « valeur »
    et « dents » — les mots qu'Oris lui montrait — et trois corrections sur quatre étaient
    rejetées alors qu'elles étaient comprises."""
    obj = dictee()
    cible = obj.facts[0].fact_id
    lecture = lire(
        {
            "nature": "dossier",
            "resume": "Je corrige l'âge.",
            "operations": [
                {"operation": "update_fact", "fact_id": cible, "changes": {"valeur": "62 ans"}}
            ],
        },
        obj,
    )
    assert lecture.nature == "dossier"
    assert lecture.operations[0].model_dump(exclude_none=True) == {
        "operation": "update_fact",
        "fact_id": cible,
        "changes": {"value": "62 ans"},
    }


def test_une_dent_remplacee_dans_un_seul_fait_garde_sa_cible() -> None:
    obj = dictee()
    cible = obj.facts[0].fact_id
    operations = normaliser(
        [{"operation": "replace_tooth", "fact_id": cible, "from_tooth": "46", "to_tooth": "36"}]
    )
    assert operations == [
        {"operation": "replace_tooth", "from_tooth": "46", "to_tooth": "36", "fact_ids": [cible]}
    ]


def test_un_fait_ajoute_en_francais_devient_un_fait_du_contrat() -> None:
    lecture = lire(
        {
            "nature": "dossier",
            "resume": "J'ajoute l'allergie.",
            "operations": [
                {
                    "operation": "add_fact",
                    "fact": {
                        "rubrique": "anamnesis",
                        "concept": "allergy",
                        "valeur": "allergie à la pénicilline",
                        "statut": "patient_reported",
                        "certitude": "certain",
                        "dents": [],
                        "champ_inconnu": "ignoré",
                    },
                }
            ],
        },
        dictee(),
    )
    assert lecture.nature == "dossier"
    fait = lecture.operations[0].model_dump()["fact"]
    assert fait["category"] == "anamnesis"
    assert fait["value"] == "allergie à la pénicilline"
    assert fait["clinical_status"] == "patient_reported"


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
    assert set(contenu["dossier"]) == {"facts", "plan_items"}
    # Les noms du contrat, pas des traductions : Claude réemploie ce qu'il a sous les yeux.
    assert {"value", "teeth", "clinical_status"} <= set(contenu["dossier"]["facts"][0])
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


def test_les_corrections_comprises_vont_jusqu_au_bout(api: Any) -> None:
    """Comprendre ne suffit pas : chaque forme que Claude rend doit s'appliquer."""
    identifiant, version = consultation(api)
    objet = api.get(f"/encounters/{identifiant}/clinical-object").json()["clinical_object"]
    fait = objet["facts"][0]

    def appliquer(operations: list[dict[str, Any]], attendue: int) -> int:
        reponse = api.post(
            f"/encounters/{identifiant}/assistant/appliquer",
            json={
                "nature": "dossier",
                "operations": operations,
                "expected_object_version": attendue,
            },
        )
        assert reponse.status_code == 200, reponse.text
        return int(reponse.json()["object_version"])

    version = appliquer(
        [
            {
                "operation": "update_fact",
                "fact_id": fait["fact_id"],
                "changes": {"value": "sensibilité au froid vif"},
            }
        ],
        version,
    )
    version = appliquer(
        [
            {
                "operation": "add_fact",
                "fact": {
                    "category": "anamnesis",
                    "concept": "allergy",
                    "value": "allergie à la pénicilline",
                    "teeth": [],
                    "assertion": "present",
                    "temporality": "current",
                    "clinical_status": "patient_reported",
                    "certainty": "certain",
                },
            }
        ],
        version,
    )
    version = appliquer([{"operation": "remove_fact", "fact_id": fait["fact_id"]}], version)

    faits = api.get(f"/encounters/{identifiant}/clinical-object").json()["clinical_object"]["facts"]
    assert fait["fact_id"] not in {f["fact_id"] for f in faits}
    assert any(f["value"] == "allergie à la pénicilline" for f in faits)


# --- L'historique, gardé sur le serveur ---------------------------------------------


def test_la_conversation_est_gardee_et_marquee_sur_le_serveur(api: Any) -> None:
    """Franck, le 11/11/2026 : la conversation ne doit pas repartir vierge, même l'app
    fermée — elle vit donc en base, et se retrouve d'un appareil à l'autre."""
    identifiant, _ = consultation(api)

    lecture = api.post(f"/encounters/{identifiant}/assistant", json={"demande": "plus court"})
    assert lecture.status_code == 200, lecture.text
    demande_id = lecture.json()["demande_id"]

    historique = api.get(f"/encounters/{identifiant}/assistant").json()
    assert [(d["texte"], d["etat"]) for d in historique] == [("plus court", "proposee")]
    assert historique[0]["lecture"]["nature"] == "redaction"

    applique = api.post(
        f"/encounters/{identifiant}/assistant/appliquer",
        json={"nature": "redaction", "consignes": ["Faire plus court"], "demande_id": demande_id},
    )
    assert applique.status_code == 200, applique.text
    fini = api.get(f"/encounters/{identifiant}/assistant").json()[0]
    assert fini["etat"] == "traitee"
    assert fini["message"].startswith("Document rédigé")

    autre = api.post(f"/encounters/{identifiant}/assistant", json={"demande": "plus court"})
    annule = api.post(f"/encounters/{identifiant}/assistant/{autre.json()['demande_id']}/annuler")
    assert annule.json()["etat"] == "annulee"
    assert [d["etat"] for d in api.get(f"/encounters/{identifiant}/assistant").json()] == [
        "traitee",
        "annulee",
    ]


def test_une_application_refusee_reste_marquee_non_aboutie(api: Any) -> None:
    identifiant, _ = consultation(api)
    lecture = api.post(f"/encounters/{identifiant}/assistant", json={"demande": "plus court"})
    refus = api.post(
        f"/encounters/{identifiant}/assistant/appliquer",
        json={
            "nature": "dossier",
            "operations": [{"operation": "replace_tooth", "from_tooth": "26", "to_tooth": "27"}],
            "demande_id": lecture.json()["demande_id"],
        },
    )
    assert refus.status_code == 409
    demande = api.get(f"/encounters/{identifiant}/assistant").json()[0]
    assert demande["etat"] == "echec"
    assert demande["code"] == "OBJECT_VERSION_REQUIRED"


# --- Une demande ne reste jamais « en cours » (PIRA, 13/11/2026) ------------------------


def test_une_panne_imprevue_rend_la_demande_non_aboutie(api: Any, monkeypatch: Any) -> None:
    """Une erreur imprévue (ici, une panne de base) laissait la demande « en cours » : l'écran
    a attendu deux jours, sans pouvoir l'interrompre."""
    from oris_api.api import assistant as route

    identifiant, _ = consultation(api)
    lecture = api.post(f"/encounters/{identifiant}/assistant", json={"demande": "plus court"})

    def panne(*_: Any, **__: Any) -> str:
        raise RuntimeError("panne imprévue")

    monkeypatch.setattr(route, "_appliquer", panne)
    with pytest.raises(RuntimeError):
        api.post(
            f"/encounters/{identifiant}/assistant/appliquer",
            json={
                "nature": "redaction",
                "consignes": ["Faire plus court"],
                "demande_id": lecture.json()["demande_id"],
            },
        )
    demande = api.get(f"/encounters/{identifiant}/assistant").json()[0]
    assert demande["etat"] == "echec"
    assert "Relancez-la" in demande["message"]


def test_une_demande_en_cours_depuis_trop_longtemps_est_dite_interrompue(
    api: Any, migrated_engine: Any
) -> None:
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import update

    from oris_api.db.models import DemandeCorrectionRow

    identifiant, _ = consultation(api)
    lecture = api.post(f"/encounters/{identifiant}/assistant", json={"demande": "plus court"})
    with migrated_engine.begin() as connexion:
        connexion.execute(
            update(DemandeCorrectionRow)
            .where(DemandeCorrectionRow.id == lecture.json()["demande_id"])
            .values(etat="application", updated_at=datetime.now(UTC) - timedelta(hours=2))
        )
    demande = api.get(f"/encounters/{identifiant}/assistant").json()[0]
    assert demande["etat"] == "echec"
    assert "Relancez-la" in demande["message"]


def test_une_version_ecrite_pendant_la_reecriture_ne_fait_pas_planter() -> None:
    """Le numéro suivant vient de la base, pas de la version courante gardée en mémoire."""
    from oris_api.db.models import DocumentRow, DocumentVersion
    from oris_api.services.documents import prochaine_version

    class Seance:
        def scalar(self, _requete: Any) -> int:
            return 2  # une version 2 écrite entre-temps par un autre écran

    document = DocumentRow(document_type="consultation_note", status="draft_ai")
    assert prochaine_version(Seance(), document) == 3  # type: ignore[arg-type]
    assert DocumentVersion  # le contrat d'unicité (document, version) reste en place


def test_une_correction_arretee_en_cours_ne_garde_rien(
    api: Any, migrated_engine: Any, monkeypatch: Any
) -> None:
    """« Pas possible d'interrompre » (15/11/2026) : arrêtée pendant que Claude travaille,
    la correction finit sans rien enregistrer."""
    from sqlalchemy import update

    from oris_api.api import assistant as route
    from oris_api.db.models import DemandeCorrectionRow

    identifiant, _ = consultation(api)
    lecture = api.post(f"/encounters/{identifiant}/assistant", json={"demande": "plus court"})
    demande_id = lecture.json()["demande_id"]
    original = route._appliquer

    def puis_arretee(*args: Any, **kwargs: Any) -> str:
        message = original(*args, **kwargs)
        # Pendant ce temps, sur un autre écran : « Arrêter ».
        with migrated_engine.begin() as connexion:
            connexion.execute(
                update(DemandeCorrectionRow)
                .where(DemandeCorrectionRow.id == demande_id)
                .values(etat="annulee")
            )
        return message

    monkeypatch.setattr(route, "_appliquer", puis_arretee)
    reponse = api.post(
        f"/encounters/{identifiant}/assistant/appliquer",
        json={"nature": "redaction", "consignes": ["Faire plus court"], "demande_id": demande_id},
    )
    assert reponse.status_code == 200
    assert reponse.json()["applique"] is False
    assert api.get(f"/encounters/{identifiant}/consignes").json()["consultation"] == []
    assert api.get(f"/encounters/{identifiant}/assistant").json()[0]["etat"] == "annulee"


def test_une_correction_en_cours_peut_etre_arretee(api: Any, migrated_engine: Any) -> None:
    from sqlalchemy import update

    from oris_api.db.models import DemandeCorrectionRow

    identifiant, _ = consultation(api)
    lecture = api.post(f"/encounters/{identifiant}/assistant", json={"demande": "plus court"})
    demande_id = lecture.json()["demande_id"]
    with migrated_engine.begin() as connexion:
        connexion.execute(
            update(DemandeCorrectionRow)
            .where(DemandeCorrectionRow.id == demande_id)
            .values(etat="application")
        )
    arret = api.post(f"/encounters/{identifiant}/assistant/{demande_id}/annuler")
    assert arret.json()["etat"] == "annulee"
