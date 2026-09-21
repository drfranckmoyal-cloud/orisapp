"""Rédaction par Claude : ce qu'Oris accepte, ce qu'il refuse, et le repli.

Le modèle est simulé : ces tests tiennent les règles de contrôle, pas la qualité de
l'écriture. Toute copie qui ajoute, omet ou déforme repart vers les gabarits.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx

from oris_api.llm.redaction import AnthropicDocumentWriter, rubriques_de
from oris_api.providers.mock import MockDocumentGenerationProvider
from tests.test_redaction_consultation import dictee


def writer(copies: list[dict[str, Any]]) -> tuple[AnthropicDocumentWriter, list[dict[str, Any]]]:
    envoyes: list[dict[str, Any]] = []

    def repondre(request: httpx.Request) -> httpx.Response:
        envoyes.append(json.loads(request.content))
        copie = copies[min(len(envoyes) - 1, len(copies) - 1)]
        return httpx.Response(
            200,
            json={
                "content": [{"type": "tool_use", "name": "rediger_compte_rendu", "input": copie}]
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(repondre))
    return AnthropicDocumentWriter(
        "cle", "modele", MockDocumentGenerationProvider(), client
    ), envoyes


def copie_fidele() -> dict[str, Any]:
    """Une copie qui reprend chaque rubrique en une phrase citant tous ses faits."""
    base = asyncio.run(MockDocumentGenerationProvider().generate(dictee(), "consultation_note"))
    return {
        "rubriques": [
            {
                "titre": r.titre,
                "phrases": [
                    {"texte": " ".join(c.text for c in r.claims), "fact_ids": sorted(r.fact_ids)}
                ],
            }
            for r in rubriques_de(base)
        ]
    }


def test_a_faithful_copy_is_accepted_and_cites_every_fact() -> None:
    redacteur, _ = writer([copie_fidele()])
    document = asyncio.run(redacteur.generate(dictee(), "consultation_note"))
    assert document.generator == ""
    assert set(document.supported_fact_ids) == {f.fact_id for f in dictee().facts}


def test_the_model_sees_facts_never_the_patient_name() -> None:
    redacteur, envoyes = writer([copie_fidele()])
    asyncio.run(redacteur.generate(dictee(), "consultation_note"))
    contenu = envoyes[0]["messages"][0]["content"]
    assert "patient_id" not in contenu and "pat" not in json.loads(contenu).get("patient", "")


def test_an_invented_tooth_is_refused_then_falls_back() -> None:
    fausse = copie_fidele()
    fausse["rubriques"][1]["phrases"][0]["texte"] += " Carie sur 36."
    redacteur, envoyes = writer([fausse])
    document = asyncio.run(redacteur.generate(dictee(), "consultation_note"))
    assert "(repli)" in document.generator
    assert "36" not in document.content
    assert len(envoyes) == 2  # un nouvel essai, expliqué
    assert "dent absente" in envoyes[1]["messages"][-1]["content"]


def test_an_invented_number_is_refused() -> None:
    fausse = copie_fidele()
    fausse["rubriques"][3]["phrases"][0]["texte"] += " Durée prévue : 6 mois."
    redacteur, _ = writer([fausse])
    document = asyncio.run(redacteur.generate(dictee(), "consultation_note"))
    assert "(repli)" in document.generator


def test_a_forgotten_fact_is_refused() -> None:
    fausse = copie_fidele()
    fausse["rubriques"][1]["phrases"][0]["fact_ids"] = fausse["rubriques"][1]["phrases"][0][
        "fact_ids"
    ][:1]
    redacteur, _ = writer([fausse])
    assert "(repli)" in asyncio.run(redacteur.generate(dictee(), "consultation_note")).generator


def test_a_second_attempt_that_complies_is_kept() -> None:
    fausse = copie_fidele()
    fausse["rubriques"][1]["phrases"][0]["texte"] += " Carie sur 36."
    redacteur, envoyes = writer([fausse, copie_fidele()])
    document = asyncio.run(redacteur.generate(dictee(), "consultation_note"))
    assert document.generator == "" and len(envoyes) == 2


def test_a_lost_refusal_is_refused() -> None:
    fausse = copie_fidele()
    derniere = fausse["rubriques"][-1]["phrases"][0]
    derniere["texte"] = "Implants et orthodontie évoqués, solution implantaire impossible (12, 22)."
    redacteur, _ = writer([fausse])
    assert "(repli)" in asyncio.run(redacteur.generate(dictee(), "consultation_note")).generator


def test_the_treatment_plan_is_never_sent() -> None:
    redacteur, envoyes = writer([copie_fidele()])
    asyncio.run(redacteur.generate(dictee(), "treatment_plan_text"))
    assert envoyes == []


def test_a_network_failure_falls_back_silently_to_the_templates() -> None:
    def panne(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("hors ligne")

    client = httpx.AsyncClient(transport=httpx.MockTransport(panne))
    redacteur = AnthropicDocumentWriter("cle", "modele", MockDocumentGenerationProvider(), client)
    document = asyncio.run(redacteur.generate(dictee(), "consultation_note"))
    assert "(repli)" in document.generator
    assert "Agénésie de 12 et 22" in document.content
