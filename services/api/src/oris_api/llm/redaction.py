"""Rédaction des comptes rendus par Claude, sous le contrôle d'Oris.

Le partage des rôles est strict :

- **Oris range.** Les gabarits déterministes décident quelle information va dans quelle
  rubrique (docs/MODELES_CR.md) et écrivent une phrase par fait. C'est la version de
  repli, déjà sûre.
- **Claude rédige.** Rubrique par rubrique, il transforme ces phrases en paragraphes
  liés, sans doublon, en citant pour chaque phrase les faits qui l'appuient. Il ne voit
  que les faits — jamais le transcript, jamais le nom du patient (D008).
- **Oris vérifie tout.** Même rubriques, aucun fait oublié, aucun fait cité hors de sa
  rubrique, aucune dent ni aucun chiffre qui ne vienne des faits cités, négation,
  incertitude et refus toujours dits. Une copie refusée a droit à un nouvel essai
  expliqué ; ensuite, c'est la version de repli qui part. Jamais de correction en
  silence.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

import httpx

from oris_api.contracts import ClinicalEncounter, ClinicalFact
from oris_api.contracts.generated import DocumentDocumentType
from oris_api.documents.renderer import (
    DEFAULT_STYLE,
    INCERTITUDE,
    LIMITS_SECTION,
    NEGATION,
    Style,
    render_content,
)
from oris_api.domain.types import Claim, GeneratedDocument
from oris_api.providers.base import DocumentGenerationProvider, ProviderInfo

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"
PROMPT_VERSION = "redaction-fr-3"
MAX_TOKENS = 6_000
MAX_ATTEMPTS = 2
TOOL_NAME = "rediger_compte_rendu"

#: Documents en paragraphes : ceux-là seulement sont réécrits. Le plan garde sa forme,
#: élément par élément (seuls ses titres sont proposés par Claude) ; le compte rendu
#: opératoire garde ses emplacements.
REDIGES: frozenset[str] = frozenset({"consultation_note", "referral_letter"})
TITRES_TOOL = "titrer_etapes"
TITRES_PROMPT = """Tu donnes un titre court à chaque étape d'un plan de traitement dentaire \
français : 2 à 4 mots, au registre d'un praticien (« Greffe de conjonctif », \
« Gouttière conformatrice », « Bridges cantilever », « Préparation puis collage »). \
N'utilise que des mots présents dans l'action de l'étape : aucun mot, aucune dent, \
aucun chiffre en plus. Le reste de l'action sera affiché sous le titre : ne cherche pas \
à tout dire."""
MOTS_TITRE_MAX = 5

SYSTEM_PROMPT = """Tu rédiges des comptes rendus dentaires pour un chirurgien-dentiste \
français, dans un registre professionnel, rédigé et précis, tel qu'il l'écrirait lui-même \
à un confrère. Tu reçois, rubrique par rubrique, des faits cliniques déjà établis et une \
première formulation, phrase par phrase. Ta tâche : réécrire chaque rubrique en un \
paragraphe fluide et lié, sans redite, en phrases complètes.

Règles absolues :
- n'ajoute AUCUNE information : pas de fait, pas de dent, pas de chiffre, pas de durée, \
pas de matériau, pas d'interprétation qui ne soit dans les faits fournis ;
- n'omets aucun fait : chaque fait de la rubrique est repris au moins une fois ;
- chaque phrase cite dans `fact_ids` tous les faits qu'elle reprend, et seulement des \
faits de sa rubrique ;
- préserve la négation (« pas de », « absence de »), l'incertitude (« possible », « non \
confirmé »), la temporalité (« antérieurement », « déjà ») et le statut (proposé, \
refusé, réalisé, prévu) exactement ;
- une information rapportée par le patient reste attribuée au patient ;
- n'établis aucun lien de cause ou de but entre deux faits (« en raison de », « afin \
de », « donc ») s'il n'est pas déjà dans l'un d'eux : juxtapose-les plutôt ;
- recopie les numéros de dents tels quels (notation FDI) ;
- garde les titres des rubriques à l'identique et dans le même ordre ;
- pas de formule d'appel ni de signature, pas de mise en forme (ni puces, ni gras) ;
- deux faits qui disent la même chose tiennent en une seule phrase qui les cite tous \
les deux.

Mise en page, pour un texte aéré et lisible d'un coup d'œil :
- découpe chaque rubrique en paragraphes courts, une idée chacun (une à trois phrases) ; \
marque `nouveau_paragraphe: true` sur la première phrase de chaque nouveau paragraphe ;
- mets en gras, entre doubles astérisques (**ainsi**), les seuls éléments clés : \
diagnostic, traitement proposé ou réalisé, dents concernées, refus, alerte — un ou deux \
passages courts par paragraphe au plus, jamais une phrase entière ; aucune autre mise \
en forme."""

TOOL_DESCRIPTION = "Enregistre le compte rendu rédigé, rubrique par rubrique."


def tool_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["rubriques"],
        "properties": {
            "rubriques": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["titre", "phrases"],
                    "properties": {
                        "titre": {"type": "string"},
                        "phrases": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "required": ["texte", "fact_ids"],
                                "properties": {
                                    "texte": {"type": "string"},
                                    "fact_ids": {"type": "array", "items": {"type": "string"}},
                                    "nouveau_paragraphe": {"type": "boolean"},
                                },
                            },
                        },
                    },
                },
            }
        },
    }


class RedactionRefusee(ValueError):
    """La copie ne respecte pas une règle : elle ne part pas."""


@dataclass(frozen=True)
class Rubrique:
    titre: str
    claims: tuple[Claim, ...]

    @property
    def fact_ids(self) -> set[str]:
        return {fid for claim in self.claims for fid in claim.fact_ids}


def rubriques_de(document: GeneratedDocument) -> list[Rubrique]:
    """Les rubriques de la version de repli, hors « Limites » (qui ne se réécrit pas)."""
    ordre: list[str] = []
    par_titre: dict[str, list[Claim]] = {}
    for claim in document.claims:
        if claim.section == LIMITS_SECTION:
            continue
        if claim.section not in par_titre:
            ordre.append(claim.section)
            par_titre[claim.section] = []
        par_titre[claim.section].append(claim)
    return [Rubrique(titre, tuple(par_titre[titre])) for titre in ordre]


def _fait(fact: ClinicalFact) -> dict[str, Any]:
    return {
        "fact_id": fact.fact_id,
        "valeur": fact.value if isinstance(fact.value, str) else json.dumps(fact.value),
        "dents": list(fact.teeth),
        "assertion": fact.assertion,
        "statut": fact.clinical_status,
        "temporalite": fact.temporality,
        "certitude": fact.certainty,
    }


def message(rubriques: list[Rubrique], facts: dict[str, ClinicalFact], style: Style) -> str:
    payload = {
        "longueur": "concise" if style.length == "concise" else "standard",
        "rubriques": [
            {
                "titre": rubrique.titre,
                "premiere_formulation": [claim.text for claim in rubrique.claims],
                "faits": [_fait(facts[fid]) for fid in sorted(rubrique.fact_ids) if fid in facts],
            }
            for rubrique in rubriques
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=1)


NOMBRE = re.compile(r"\d+(?:[.,]\d+)?")
DENT = re.compile(r"(?<![\d,.])([1-4][1-8]|[5-8][1-5])(?![\d,.]\d)")


def _nombres(texte: str) -> set[str]:
    return {n.replace(",", ".") for n in NOMBRE.findall(texte)}


def verifier(
    rubriques: list[Rubrique],
    sortie: dict[str, Any],
    facts: dict[str, ClinicalFact],
) -> list[Claim]:
    """Contrôle la copie. Renvoie les phrases acceptées, ou lève `RedactionRefusee`."""
    rendues = sortie.get("rubriques")
    if not isinstance(rendues, list):
        raise RedactionRefusee("sortie sans rubriques")
    attendus = [r.titre for r in rubriques]
    titres = [r.get("titre") for r in rendues if isinstance(r, dict)]
    if titres != attendus:
        raise RedactionRefusee(f"rubriques attendues {attendus}, reçues {titres}")

    claims: list[Claim] = []
    for rubrique, rendue in zip(rubriques, rendues, strict=True):
        couverts: set[str] = set()
        paragraphe = -1
        for phrase in rendue.get("phrases") or []:
            texte = str(phrase.get("texte", "")).strip()
            if paragraphe < 0 or phrase.get("nouveau_paragraphe"):
                paragraphe += 1
            _controler_gras(texte, rubrique.titre)
            cites = [str(fid) for fid in phrase.get("fact_ids") or []]
            if not texte or not cites:
                raise RedactionRefusee(f"phrase sans fait d'appui dans « {rubrique.titre} »")
            hors = set(cites) - rubrique.fact_ids
            if hors:
                raise RedactionRefusee(
                    f"« {rubrique.titre} » cite des faits d'une autre rubrique : {sorted(hors)}"
                )
            appui = [facts[fid] for fid in cites if fid in facts]
            _controler_phrase(sans_gras(texte), appui, rubrique.titre)
            couverts |= set(cites)
            claims.append(
                Claim(
                    rubrique.titre,
                    texte,
                    fact_ids=tuple(dict.fromkeys(cites)),
                    paragraphe=paragraphe,
                )
            )
        oublies = rubrique.fact_ids - couverts
        if oublies:
            raise RedactionRefusee(f"faits omis dans « {rubrique.titre} » : {sorted(oublies)}")
    return claims


GRAS = re.compile(r"\*\*(.+?)\*\*")
GRAS_MOTS_MAX = 8


def sans_gras(texte: str) -> str:
    return texte.replace("**", "")


def _controler_gras(texte: str, titre: str) -> None:
    """Le gras souligne un mot-clé ; il ne met pas une phrase entière en avant."""
    if texte.count("**") % 2:
        raise RedactionRefusee(f"gras mal fermé dans « {titre} »")
    for passage in GRAS.findall(texte):
        if len(passage.split()) > GRAS_MOTS_MAX:
            raise RedactionRefusee(f"passage en gras trop long dans « {titre} » : « {passage} »")


def _controler_phrase(texte: str, appui: list[ClinicalFact], titre: str) -> None:
    source = " ".join(
        (f.value if isinstance(f.value, str) else json.dumps(f.value)) + " " + " ".join(f.teeth)
        for f in appui
    )
    dents = set(DENT.findall(texte)) - {t for f in appui for t in f.teeth}
    if dents - set(DENT.findall(source)):
        raise RedactionRefusee(f"dent absente des faits cités dans « {titre} » : {sorted(dents)}")
    inventes = _nombres(texte) - _nombres(source)
    if inventes:
        raise RedactionRefusee(
            f"chiffre absent des faits cités dans « {titre} » : {sorted(inventes)}"
        )
    if any(f.assertion == "absent" for f in appui) and not NEGATION.search(texte):
        raise RedactionRefusee(f"négation perdue dans « {titre} » : « {texte} »")
    incertain = any(
        f.assertion == "uncertain" or f.certainty in {"possible", "probable"} for f in appui
    )
    if incertain and not (INCERTITUDE.search(texte) or "non confirmé" in texte):
        raise RedactionRefusee(f"incertitude perdue dans « {titre} » : « {texte} »")
    if any(f.clinical_status == "refused" for f in appui) and not re.search(
        r"refus|décline|ne souhaite pas", texte, re.IGNORECASE
    ):
        raise RedactionRefusee(f"refus perdu dans « {titre} » : « {texte} »")


class AnthropicDocumentWriter:
    """`DocumentGenerationProvider` : gabarits d'Oris, puis rédaction contrôlée par Claude."""

    def __init__(
        self,
        api_key: str,
        model: str,
        repli: DocumentGenerationProvider,
        client: httpx.AsyncClient | None = None,
        timeout_s: float = 90,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._repli = repli
        self._client = client
        self._timeout = timeout_s
        self.info = ProviderInfo(
            name="anthropic",
            version=f"{model}/{PROMPT_VERSION}",
            capabilities=["redaction", "french"],
        )
        self.dernier_refus: str | None = None

    async def generate(
        self,
        encounter: ClinicalEncounter,
        document_type: DocumentDocumentType,
        style: Style | None = None,
    ) -> GeneratedDocument:
        style = style or DEFAULT_STYLE
        if document_type == "treatment_plan_text":
            return await self._plan(encounter)
        base = await self._repli.generate(encounter, document_type, style)
        if document_type not in REDIGES:
            return base
        rubriques = rubriques_de(base)
        if not rubriques:
            return base
        facts = {fact.fact_id: fact for fact in encounter.facts}
        repli = f"{self._repli.info.name}:{self._repli.info.version} (repli)"
        messages: list[dict[str, Any]] = [
            {"role": "user", "content": message(rubriques, facts, style)}
        ]
        for essai in range(MAX_ATTEMPTS):
            try:
                sortie = await self._appeler(messages)
            except (httpx.HTTPError, RedactionRefusee, KeyError, ValueError) as error:
                self.dernier_refus = f"appel : {error}"[:300]
                return _avec_generateur(base, repli)
            try:
                claims = verifier(rubriques, sortie, facts)
            except RedactionRefusee as refus:
                self.dernier_refus = str(refus)[:300]
                if essai == MAX_ATTEMPTS - 1:
                    return _avec_generateur(base, repli)
                messages += [
                    {
                        "role": "assistant",
                        "content": [
                            {"type": "text", "text": json.dumps(sortie, ensure_ascii=False)}
                        ],
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Copie refusée : {refus}. Corrige ce point et renvoie la copie "
                            "complète, sans rien ajouter qui ne soit dans les faits."
                        ),
                    },
                ]
                continue
            limites = tuple(c for c in base.claims if c.section == LIMITS_SECTION)
            tout = (*limites, *claims)
            self.dernier_refus = None
            return GeneratedDocument(document_type, render_content(tout), tout)
        return _avec_generateur(base, repli)

    async def _plan(self, encounter: ClinicalEncounter) -> GeneratedDocument:
        """Le plan garde sa forme ; Claude ne fait que proposer des titres courts."""
        from oris_api.documents.renderer import render_treatment_plan

        plan = encounter.treatment_plan
        items = list(plan.items) if plan else []
        if not items:
            return render_treatment_plan(encounter)
        demande = json.dumps(
            {"etapes": [{"item_id": i.item_id, "action": i.action} for i in items]},
            ensure_ascii=False,
        )
        try:
            sortie = await self._appeler(
                [{"role": "user", "content": demande}],
                system=TITRES_PROMPT,
                tool=(TITRES_TOOL, "Enregistre un titre court par étape.", titres_schema()),
            )
            titres = verifier_titres({i.item_id: i.action for i in items}, sortie)
        except (httpx.HTTPError, RedactionRefusee, KeyError, ValueError) as error:
            self.dernier_refus = f"titres : {error}"[:300]
            document = render_treatment_plan(encounter)
            return _avec_generateur(
                document, f"{self._repli.info.name}:{self._repli.info.version} (repli)"
            )
        return render_treatment_plan(encounter, titres)

    async def _appeler(
        self,
        messages: list[dict[str, Any]],
        system: str = SYSTEM_PROMPT,
        tool: tuple[str, str, dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        nom, description, schema = tool or (TOOL_NAME, TOOL_DESCRIPTION, tool_schema())
        body = {
            "model": self._model,
            "max_tokens": MAX_TOKENS,
            "system": system,
            "messages": messages,
            "tools": [{"name": nom, "description": description, "input_schema": schema}],
            "tool_choice": {"type": "tool", "name": nom},
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
        finally:
            if self._client is None:
                await client.aclose()
        if response.status_code >= 400:
            raise ValueError(f"HTTP {response.status_code}")
        for block in response.json().get("content") or []:
            if block.get("type") == "tool_use" and block.get("name") == nom:
                return dict(block.get("input") or {})
        raise ValueError("pas de sortie d'outil")


def titres_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["titres"],
        "properties": {
            "titres": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["item_id", "titre"],
                    "properties": {"item_id": {"type": "string"}, "titre": {"type": "string"}},
                },
            }
        },
    }


def _racines(texte: str) -> set[str]:
    """Les mots porteurs de sens, réduits à leurs cinq premières lettres (bridge/bridges)."""
    mots = re.findall(r"[a-zàâäéèêëîïôöùûüç]+", texte.lower())
    return {m[:5] for m in mots if len(m) > 3}


def verifier_titres(actions: dict[str, str], sortie: dict[str, Any]) -> dict[str, str]:
    """Un titre par étape, court, fait seulement de mots de l'action."""
    titres: dict[str, str] = {}
    for entree in sortie.get("titres") or []:
        item_id = str(entree.get("item_id", ""))
        titre = str(entree.get("titre", "")).strip().rstrip(".")
        if item_id not in actions or not titre:
            raise RedactionRefusee(f"titre sans étape connue : {item_id}")
        if len(titre.split()) > MOTS_TITRE_MAX:
            raise RedactionRefusee(f"titre trop long : « {titre} »")
        action = actions[item_id]
        if _racines(titre) - _racines(action):
            raise RedactionRefusee(f"mot absent de l'action dans « {titre} »")
        if _nombres(titre) - _nombres(action) or DENT.findall(titre):
            raise RedactionRefusee(f"chiffre ou dent en plus dans « {titre} »")
        titres[item_id] = titre[:1].upper() + titre[1:]
    if set(titres) != set(actions):
        raise RedactionRefusee("une étape n'a pas de titre")
    return titres


def _avec_generateur(document: GeneratedDocument, generateur: str) -> GeneratedDocument:
    return GeneratedDocument(
        document.document_type, document.content, document.claims, generator=generateur
    )
