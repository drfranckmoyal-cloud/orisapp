"""Attribution des rôles par le modèle de langue, quand les règles ne tranchent pas.

Ce fournisseur ne voit que des **extraits de paroles regroupés par voix**, et ne rend
qu'une chose : un rôle par voix. Il ne produit aucun fait clinique, ne réécrit rien, et
n'a pas accès au dossier. Un rôle rendu sans assurance suffisante est refusé : mieux
vaut `unknown` et l'alerte qui va avec qu'une impression du patient écrite comme un
constat du praticien (invariant 5).

Le texte du prompt est versionné avec le code (`PROMPT_VERSION`) : toute évolution est
traçable et se mesure au banc d'essai.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx

from oris_api.domain.speaker_roles import Parole, Voix
from oris_api.llm.tool_output import deballer
from oris_api.providers.base import ProviderInfo, SpeakerRolesUnavailable

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"
DEFAULT_MODEL = "claude-sonnet-5"
MAX_TOKENS = 1_000
#: Une réponse par passage : il en faut la place. 50 passages tiennent largement.
MAX_TOKENS_PAROLES = 4_000
#: Découpage des longues consultations, avec quelques passages de contexte devant :
#: qui parle se lit dans l'enchaînement des tours de parole.
FENETRE = 50
CONTEXTE = 5
PROMPT_VERSION = "roles-fr-1"
TRANSIENT_BACKOFF_S = (1.0, 4.0)

#: En dessous, le rôle n'est pas posé : l'alerte « voix non attribuées » vaut mieux.
SEUIL_CONFIANCE = 0.8

ROLES = ("practitioner", "patient", "assistant", "companion", "unknown")

TOOL_NAME = "attribuer_les_voix"
TOOL_DESCRIPTION = "Donne son rôle à chaque voix de la consultation, d'après ses seules paroles."

SYSTEM_PROMPT = """Tu attribues un rôle à chaque voix d'une consultation dentaire \
enregistrée en France. Tu ne rédiges rien, tu n'extrais aucun fait clinique, tu ne \
corriges aucune parole : tu dis seulement, pour chaque voix, qui parle.

Rôles possibles :
- `practitioner` : le chirurgien-dentiste. Il examine, explique, annonce ce qu'il fait \
et ce qu'il va faire, pose les questions, emploie les numéros de dents et le vocabulaire \
technique en le maîtrisant.
- `patient` : la personne soignée. Elle décrit ce qu'elle ressent, répond, demande, \
accepte ou refuse. Elle peut employer des mots techniques sans être praticien.
- `assistant` : l'assistante dentaire. Elle assiste le praticien, prépare, passe les \
instruments, parle peu de la décision de soin.
- `companion` : un accompagnant (parent, conjoint) qui parle pour ou avec le patient.
- `unknown` : tu n'es pas sûr.

Règles :
- une voix ne reçoit un rôle que si ses propres paroles le montrent ; l'ordre de parole, \
la durée ou le numéro de la voix ne prouvent rien ;
- au moindre doute, réponds `unknown` : c'est une réponse juste, pas un échec ;
- `confiance` dit ton assurance entre 0 et 1 ; une voix que tu ne saurais pas défendre \
devant le praticien est en dessous de 0,8 ;
- plusieurs voix peuvent avoir le même rôle (deux extraits d'une même personne mal \
séparés) ;
- réponds pour **toutes** les voix fournies, avec exactement leurs identifiants."""

TOOL_PAROLES = "attribuer_les_paroles"
TOOL_PAROLES_DESCRIPTION = (
    "Dit qui parle dans chaque passage fourni, sans en modifier ni en ajouter aucun."
)

SYSTEM_PROMPT_PAROLES = """Tu dis qui parle dans chaque passage d'une consultation \
dentaire enregistrée en France. La transcription n'a pas su séparer les voix : les \
passages se suivent dans l'ordre, tous mélangés.

Tu ne rédiges rien, tu n'extrais aucun fait clinique, tu ne corriges aucune parole. Tu \
rends un rôle par passage, et rien d'autre.

Rôles possibles :
- `practitioner` : le chirurgien-dentiste. Il examine, explique, annonce ce qu'il fait \
et ce qu'il va faire, pose les questions, emploie les numéros de dents et le vocabulaire \
technique en le maîtrisant, donne les consignes.
- `patient` : la personne soignée. Elle décrit ce qu'elle ressent, répond, demande, \
accepte ou refuse. Elle peut employer des mots techniques sans être praticien.
- `assistant` : l'assistante dentaire, qui assiste sans décider du soin.
- `companion` : un accompagnant qui parle pour ou avec le patient.
- `unknown` : tu n'es pas sûr.

Règles :
- appuie-toi sur l'enchaînement : une question appelle une réponse, une consigne appelle \
une exécution ; un passage isolé et neutre (« d'accord », « voilà ») ne prouve rien à lui \
seul, mais son tour de parole, si ;
- au moindre doute réponds `unknown` : c'est une réponse juste, pas un échec ;
- `confiance` dit ton assurance entre 0 et 1 ; en dessous de 0,8 le rôle ne sera pas posé ;
- les passages marqués `contexte` sont là pour t'aider à suivre le fil : ne les rends pas ;
- réponds pour **tous** les autres passages, avec exactement leurs identifiants."""

TOOL_PAROLES_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "paroles": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "segment_id": {"type": "string"},
                    "role": {"type": "string", "enum": list(ROLES)},
                    "confiance": {"type": "number", "minimum": 0, "maximum": 1},
                },
                "required": ["segment_id", "role", "confiance"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["paroles"],
    "additionalProperties": False,
}


TOOL_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "voix": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "label": {"type": "string"},
                    "role": {"type": "string", "enum": list(ROLES)},
                    "confiance": {"type": "number", "minimum": 0, "maximum": 1},
                },
                "required": ["label", "role", "confiance"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["voix"],
    "additionalProperties": False,
}


def user_message(voix: list[Voix]) -> str:
    return json.dumps(
        {
            "voix": [
                {
                    "label": v.label,
                    "prises_de_parole": v.segments,
                    "part_du_temps_de_parole": round(v.part, 2),
                    "extraits": v.extraits,
                }
                for v in voix
            ]
        },
        ensure_ascii=False,
        indent=2,
    )


class AnthropicSpeakerRoleProvider:
    """`SpeakerRoleProvider` : voix → rôles, sans jamais toucher au clinique."""

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        client: httpx.AsyncClient | None = None,
        timeout_s: float = 60,
        retry_backoff_s: tuple[float, ...] = TRANSIENT_BACKOFF_S,
        seuil: float = SEUIL_CONFIANCE,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._client = client
        self._timeout = timeout_s
        self._backoff = retry_backoff_s
        self._seuil = seuil
        self.info = ProviderInfo(
            name="anthropic",
            version=f"{model}/{PROMPT_VERSION}",
            capabilities=["speaker_roles", "french"],
        )

    async def attribuer(self, voix: list[Voix]) -> dict[str, str]:
        """Rôle sûr de chaque voix. Une voix douteuse n'est tout simplement pas rendue."""
        if len(voix) < 2:
            return {}
        raw = await self._call(
            user_message(voix),
            SYSTEM_PROMPT,
            TOOL_NAME,
            TOOL_DESCRIPTION,
            TOOL_SCHEMA,
            MAX_TOKENS,
        )
        connues = {v.label for v in voix}
        roles: dict[str, str] = {}
        for item in raw.get("voix") or []:
            if not isinstance(item, dict):
                raise SpeakerRolesUnavailable("SPEAKER_ROLES_INVALID_OUTPUT")
            label, role = str(item.get("label", "")), str(item.get("role", ""))
            confiance = float(item.get("confiance", 0) or 0)
            # Une voix inventée ou un rôle hors liste : la sortie entière est refusée,
            # jamais rafistolée.
            if label not in connues or role not in ROLES:
                raise SpeakerRolesUnavailable("SPEAKER_ROLES_INVALID_OUTPUT")
            if role != "unknown" and confiance >= self._seuil:
                roles[label] = role
        return roles

    async def attribuer_paroles(self, paroles: list[Parole]) -> dict[str, str]:
        """Qui parle dans chaque passage, quand la transcription n'a séparé aucune voix.

        C'est le cas de toutes les vraies consultations enregistrées jusqu'ici : sans
        cela, le praticien lit « locuteur inconnu » partout.
        """
        connus = {p.segment_id for p in paroles}
        roles: dict[str, str] = {}
        refusees = 0
        fenetres = range(0, len(paroles), FENETRE)
        for debut in fenetres:
            fenetre = paroles[debut : debut + FENETRE]
            contexte = paroles[max(0, debut - CONTEXTE) : debut]
            trouve = await self._fenetre(fenetre, contexte, connus)
            if trouve is None:
                refusees += 1
                continue
            roles.update(trouve)
        # Une consultation entière refusée est une panne ; une fenêtre isolée ne l'est
        # pas : ses passages restent inconnus, les autres gardent leur rôle.
        if refusees == len(fenetres):
            raise SpeakerRolesUnavailable("SPEAKER_ROLES_INVALID_OUTPUT")
        return roles

    async def _fenetre(
        self, fenetre: list[Parole], contexte: list[Parole], connus: set[str]
    ) -> dict[str, str] | None:
        """Les rôles d'une fenêtre, ou rien si la sortie n'est pas digne de confiance.

        Un passage inventé ou un rôle hors liste fait tomber **toute la fenêtre** : une
        réponse décalée d'un cran attribuerait chaque parole au mauvais locuteur, ce qui
        est bien pire que de ne rien attribuer. Un second essai est accordé — le modèle
        ne rend pas deux fois la même sortie.
        """
        attendus = {p.segment_id for p in fenetre}
        message = self._message_paroles(fenetre, contexte)
        for essai in range(2):
            raw = await self._call(
                message,
                SYSTEM_PROMPT_PAROLES,
                TOOL_PAROLES,
                TOOL_PAROLES_DESCRIPTION,
                TOOL_PAROLES_SCHEMA,
                MAX_TOKENS_PAROLES,
            )
            trouve: dict[str, str] = {}
            refuse = False
            for item in raw.get("paroles") or []:
                if not isinstance(item, dict):
                    refuse = True
                    break
                sid, role = str(item.get("segment_id", "")), str(item.get("role", ""))
                confiance = float(item.get("confiance", 0) or 0)
                if sid not in connus or role not in ROLES:
                    refuse = True
                    break
                if sid in attendus and role != "unknown" and confiance >= self._seuil:
                    trouve[sid] = role
            if not refuse:
                return trouve
            if essai == 0:
                continue
        return None

    @staticmethod
    def _message_paroles(fenetre: list[Parole], contexte: list[Parole]) -> str:
        return json.dumps(
            {
                "passages": [
                    {"segment_id": p.segment_id, "texte": p.text, "contexte": True}
                    for p in contexte
                ]
                + [{"segment_id": p.segment_id, "texte": p.text} for p in fenetre]
            },
            ensure_ascii=False,
            indent=2,
        )

    async def _call(
        self,
        message: str,
        system: str,
        tool: str,
        description: str,
        schema: dict[str, Any],
        max_tokens: int,
    ) -> dict[str, Any]:
        for attempt in range(len(self._backoff) + 1):
            try:
                return await self._call_once(message, system, tool, description, schema, max_tokens)
            except SpeakerRolesUnavailable as error:
                transient = error.code == "ANTHROPIC_NETWORK" or error.code.startswith(
                    ("ANTHROPIC_HTTP_429", "ANTHROPIC_HTTP_5")
                )
                if not transient or attempt == len(self._backoff):
                    raise
                await asyncio.sleep(self._backoff[attempt])
        raise SpeakerRolesUnavailable("ANTHROPIC_NETWORK")

    async def _call_once(
        self,
        message: str,
        system: str,
        tool: str,
        description: str,
        schema: dict[str, Any],
        max_tokens: int,
    ) -> dict[str, Any]:
        body = {
            "model": self._model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": message}],
            "tools": [{"name": tool, "description": description, "input_schema": schema}],
            "tool_choice": {"type": "tool", "name": tool},
        }
        client = self._client or httpx.AsyncClient(timeout=self._timeout)
        try:
            response = await client.post(
                API_URL,
                headers={
                    "x-api-key": self._api_key,
                    "anthropic-version": API_VERSION,
                    "content-type": "application/json",
                },
                json=body,
            )
        except httpx.HTTPError as error:
            raise SpeakerRolesUnavailable("ANTHROPIC_NETWORK") from error
        finally:
            if self._client is None:
                await client.aclose()

        if response.status_code in {401, 403}:
            raise SpeakerRolesUnavailable("ANTHROPIC_AUTH")
        if response.status_code == 429 or response.status_code >= 500:
            raise SpeakerRolesUnavailable(f"ANTHROPIC_HTTP_{response.status_code}")
        if response.status_code >= 400:
            raise SpeakerRolesUnavailable(f"ANTHROPIC_REJECTED_{response.status_code}")

        for block in response.json().get("content") or []:
            if block.get("type") == "tool_use" and block.get("name") == tool:
                return deballer(dict(block.get("input") or {}))
        raise SpeakerRolesUnavailable("ANTHROPIC_NO_TOOL_OUTPUT")
