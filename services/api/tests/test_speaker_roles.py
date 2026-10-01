"""Qui parle : les règles, puis le modèle, puis `unknown` (spec §15, invariant 5).

Ce qui est gardé ici : un rôle n'est jamais posé sans preuve dans les paroles, une
sortie de modèle mal formée est refusée en entier, et une panne du modèle ne coûte
jamais la consultation.
"""

from __future__ import annotations

import json
from dataclasses import replace
from typing import Any
from uuid import uuid4

import httpx
import pytest
from pydantic import SecretStr

from oris_api.config import Settings
from oris_api.contracts import TranscriptSegment
from oris_api.domain.speaker_roles import Parole, Voix, appliquer, paroles, sans_role, voix
from oris_api.llm.speaker_roles import AnthropicSpeakerRoleProvider
from oris_api.providers import build_providers
from oris_api.providers.base import ProviderInfo, SpeakerRolesUnavailable
from oris_api.providers.factory import build_speaker_roles
from oris_api.services.encounters import attribuer_les_voix


def segment(segment_id: str, start_ms: int, text: str) -> TranscriptSegment:
    return TranscriptSegment(
        segment_id=segment_id,
        start_ms=start_ms,
        end_ms=start_ms + 4_000,
        speaker_role="unknown",
        text=text,
        confidence=0.9,
        is_final=True,
    )


CONSULTATION = [
    segment("t1", 0, "Bonjour, installez-vous. Qu'est-ce qui vous amène aujourd'hui ?"),
    segment("t2", 5_000, "ça me lance quand je bois froid, en haut à gauche"),
    segment("t3", 10_000, "On va regarder ça. Ouvrez grand."),
    segment("t4", 15_000, "vous croyez que c'est grave docteur ?"),
]
VOIX = {"t1": "0", "t2": "1", "t3": "0", "t4": "1"}


def reponse(voix_rendues: list[dict[str, Any]]) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "content": [
                {"type": "tool_use", "name": "attribuer_les_voix", "input": {"voix": voix_rendues}}
            ],
            "usage": {"input_tokens": 10, "output_tokens": 5},
        },
    )


def guichet(response: httpx.Response, vu: dict[str, Any] | None = None) -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        if vu is not None:
            vu.update(json.loads(request.content))
        return response

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


# --- Le résumé des voix ------------------------------------------------------------


def test_each_voice_is_summarised_by_its_own_words_and_speaking_time() -> None:
    resume = {v.label: v for v in voix(CONSULTATION, VOIX)}

    assert set(resume) == {"0", "1"}
    assert resume["0"].segments == 2
    assert resume["0"].part == pytest.approx(0.5)
    assert resume["0"].premier_ms == 0
    assert "Ouvrez grand." in " ".join(resume["0"].extraits)
    # Les paroles du patient ne se retrouvent jamais dans la voix du praticien.
    assert "docteur" not in " ".join(resume["0"].extraits)


def test_a_transcript_without_separated_voices_summarises_nothing() -> None:
    assert voix(CONSULTATION, {}) == []


# --- L'application d'une décision --------------------------------------------------


def test_a_voice_without_a_role_stays_unknown_rather_than_guessed() -> None:
    poses = appliquer(CONSULTATION, VOIX, {"0": "practitioner"})

    assert [s.speaker_role for s in poses] == ["practitioner", "unknown", "practitioner", "unknown"]
    assert sans_role(poses) is True


# --- Le modèle ---------------------------------------------------------------------


@pytest.mark.anyio
async def test_the_model_only_sees_spoken_excerpts_never_the_record() -> None:
    envoye: dict[str, Any] = {}
    fournisseur = AnthropicSpeakerRoleProvider(
        "cle-essai",
        client=guichet(
            reponse(
                [
                    {"label": "0", "role": "practitioner", "confiance": 0.95},
                    {"label": "1", "role": "patient", "confiance": 0.9},
                ]
            ),
            envoye,
        ),
    )

    roles = await fournisseur.attribuer(voix(CONSULTATION, VOIX))

    assert roles == {"0": "practitioner", "1": "patient"}
    corps = json.dumps(envoye, ensure_ascii=False)
    assert "extraits" in corps
    # Rien du dossier clinique ne part avec : ni fait, ni dent, ni patient.
    assert "fact_id" not in corps and "patient_id" not in corps


@pytest.mark.anyio
async def test_a_role_the_model_does_not_assume_is_not_posed() -> None:
    fournisseur = AnthropicSpeakerRoleProvider(
        "cle-essai",
        client=guichet(
            reponse(
                [
                    {"label": "0", "role": "practitioner", "confiance": 0.62},
                    {"label": "1", "role": "unknown", "confiance": 0.99},
                ]
            )
        ),
    )

    assert await fournisseur.attribuer(voix(CONSULTATION, VOIX)) == {}


@pytest.mark.anyio
async def test_an_invented_voice_or_an_unknown_role_is_refused_whole() -> None:
    for rendu in (
        [{"label": "7", "role": "patient", "confiance": 1.0}],
        [{"label": "0", "role": "dentiste", "confiance": 1.0}],
    ):
        fournisseur = AnthropicSpeakerRoleProvider("cle-essai", client=guichet(reponse(rendu)))
        with pytest.raises(SpeakerRolesUnavailable) as refus:
            await fournisseur.attribuer(voix(CONSULTATION, VOIX))
        assert refus.value.code == "SPEAKER_ROLES_INVALID_OUTPUT"


@pytest.mark.anyio
async def test_a_single_voice_is_never_sent_to_the_model() -> None:
    fournisseur = AnthropicSpeakerRoleProvider(
        "cle-essai", client=guichet(httpx.Response(500, json={}))
    )

    assert await fournisseur.attribuer(voix(CONSULTATION, {"t1": "0", "t3": "0"})) == {}


@pytest.mark.anyio
async def test_a_refusal_by_the_model_is_said_with_its_code_not_swallowed() -> None:
    fournisseur = AnthropicSpeakerRoleProvider(
        "cle-essai", client=guichet(httpx.Response(401, json={})), retry_backoff_s=()
    )

    with pytest.raises(SpeakerRolesUnavailable) as refus:
        await fournisseur.attribuer(voix(CONSULTATION, VOIX))
    assert refus.value.code == "ANTHROPIC_AUTH"


# --- Le branchement dans le traitement ---------------------------------------------


class FauxFournisseur:
    """Rend ce qu'on lui dit de rendre, ou tombe en panne."""

    info = ProviderInfo(name="faux", version="1", capabilities=["speaker_roles"])

    def __init__(
        self,
        roles: dict[str, str] | None = None,
        panne: str | None = None,
        par_passage: dict[str, str] | None = None,
    ) -> None:
        self.roles = roles or {}
        self.panne = panne
        self.par_passage = par_passage or {}
        self.appels = 0
        self.appels_passages = 0

    async def attribuer(self, voix: list[Voix]) -> dict[str, str]:
        self.appels += 1
        if self.panne:
            raise SpeakerRolesUnavailable(self.panne)
        return self.roles

    async def attribuer_paroles(self, paroles: list[Parole]) -> dict[str, str]:
        self.appels_passages += 1
        if self.panne:
            raise SpeakerRolesUnavailable(self.panne)
        return self.par_passage


def jeu(
    roles: dict[str, str] | None = None,
    panne: str | None = None,
    par_passage: dict[str, str] | None = None,
) -> tuple[Any, Any]:
    fournisseur = FauxFournisseur(roles, panne, par_passage)
    return fournisseur, replace(build_providers(Settings()), speaker_roles=fournisseur)


def test_the_model_is_asked_only_when_the_rules_leave_a_voice_unnamed() -> None:
    fournisseur, providers = jeu({"0": "practitioner", "1": "patient"})

    poses = attribuer_les_voix(CONSULTATION, VOIX, providers, uuid4())

    assert fournisseur.appels == 1
    assert [s.speaker_role for s in poses] == [
        "practitioner",
        "patient",
        "practitioner",
        "patient",
    ]


def test_what_the_rules_decided_is_never_overwritten_by_the_model() -> None:
    # Une voix qui parle comme un praticien : les règles tranchent, le modèle dit
    # l'inverse. C'est la règle qui gagne — elle s'appuie sur des tournures, pas sur
    # une impression.
    segments = [
        segment("t1", 0, "Je note une carie sur la 26, à l'examen. On va faire un composite."),
        segment("t2", 5_000, "d'accord docteur, merci"),
    ]
    labels = {"t1": "0", "t2": "1"}
    _, providers = jeu({"0": "patient", "1": "practitioner"})

    poses = attribuer_les_voix(segments, labels, providers, uuid4())

    assert poses[0].speaker_role == "practitioner"
    assert poses[1].speaker_role == "patient"


def test_a_model_failure_costs_the_roles_not_the_consultation() -> None:
    _, providers = jeu(panne="ANTHROPIC_NETWORK")

    poses = attribuer_les_voix(CONSULTATION, VOIX, providers, uuid4())

    assert [s.text for s in poses] == [s.text for s in CONSULTATION]
    assert sans_role(poses) is True


def test_excerpts_never_leave_oris_without_the_same_consent_as_extraction() -> None:
    # `ALLOW_EXTERNAL_LLM=false` : des paroles ne peuvent pas partir chez un tiers pour
    # décider qui parle, pas plus que pour extraire les faits.
    refuse = build_speaker_roles(
        Settings(
            clinical_extraction_provider="anthropic",
            allow_external_llm=False,
            anthropic_api_key=SecretStr("cle-essai"),
        )
    )
    accepte = build_speaker_roles(
        Settings(
            clinical_extraction_provider="anthropic",
            allow_external_llm=True,
            anthropic_api_key=SecretStr("cle-essai"),
        )
    )

    assert refuse.info.name == "mock"
    assert accepte.info.name == "anthropic"


def test_without_any_separated_voice_each_passage_is_named_by_its_turn() -> None:
    # Le cas de toutes les vraies consultations : la transcription ne sépare rien.
    melange = [
        segment("t1", 0, "on regarde ça"),
        segment("t2", 5_000, "ça me lance quand je bois froid"),
        segment("t3", 10_000, "voilà"),
    ]
    fournisseur, providers = jeu(par_passage={"t1": "practitioner", "t2": "patient"})

    poses = attribuer_les_voix(melange, {}, providers, uuid4())

    assert fournisseur.appels == 0 and fournisseur.appels_passages == 1
    assert [s.speaker_role for s in poses] == [
        "practitioner",
        "patient",
        "unknown",  # passage non rendu par le modèle : inconnu, jamais deviné
    ]


def test_a_passage_the_rules_already_named_is_not_renamed_by_the_model() -> None:
    segments = [
        segment("t1", 0, "Je note une carie sur la 26, à l'examen. On va faire un composite."),
        segment("t2", 5_000, "hmm"),
    ]
    _, providers = jeu(par_passage={"t1": "patient", "t2": "patient"})

    poses = attribuer_les_voix(segments, {"t1": "0", "t2": "0"}, providers, uuid4())

    assert poses[0].speaker_role == "practitioner"
    assert poses[1].speaker_role == "patient"


def test_only_the_passages_of_the_window_are_kept_from_an_answer() -> None:
    assert [p.segment_id for p in paroles(CONSULTATION)] == ["t1", "t2", "t3", "t4"]


# --- Passage par passage : ce qui est refusé, et ce qui ne l'est pas ----------------


def paroles_longues(n: int) -> list[Parole]:
    return [Parole(segment_id=f"t{i + 1}", text=f"passage {i + 1}") for i in range(n)]


def reponse_paroles(items: list[dict[str, Any]]) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "content": [
                {
                    "type": "tool_use",
                    "name": "attribuer_les_paroles",
                    "input": {"paroles": items},
                }
            ]
        },
    )


@pytest.mark.anyio
async def test_a_misaligned_window_is_dropped_whole_not_applied_one_off() -> None:
    """Une réponse décalée attribuerait chaque parole au mauvais locuteur."""
    appels = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        appels["n"] += 1
        envoye = json.loads(request.content)
        premiere = json.loads(envoye["messages"][0]["content"])["passages"][0]["segment_id"]
        if premiere == "t1":  # première fenêtre : une parole inventée
            return reponse_paroles(
                [
                    {"segment_id": "t1", "role": "practitioner", "confiance": 1.0},
                    {"segment_id": "t999", "role": "patient", "confiance": 1.0},
                ]
            )
        return reponse_paroles([{"segment_id": "t51", "role": "patient", "confiance": 1.0}])

    fournisseur = AnthropicSpeakerRoleProvider(
        "cle-essai", client=httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )

    roles = await fournisseur.attribuer_paroles(paroles_longues(51))

    # La fenêtre fautive ne donne rien, même pour son passage valide ; l'autre tient.
    assert roles == {"t51": "patient"}
    # Un second essai a été accordé à la fenêtre refusée avant de l'abandonner.
    assert appels["n"] == 3


@pytest.mark.anyio
async def test_a_consultation_refused_from_end_to_end_is_a_failure_not_a_silence() -> None:
    fournisseur = AnthropicSpeakerRoleProvider(
        "cle-essai",
        client=httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda request: reponse_paroles(
                    [{"segment_id": "inventé", "role": "patient", "confiance": 1.0}]
                )
            )
        ),
    )

    with pytest.raises(SpeakerRolesUnavailable) as refus:
        await fournisseur.attribuer_paroles(paroles_longues(3))
    assert refus.value.code == "SPEAKER_ROLES_INVALID_OUTPUT"
