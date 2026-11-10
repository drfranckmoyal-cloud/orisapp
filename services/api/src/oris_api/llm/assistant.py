"""Le dialogue de correction : une phrase du praticien, comprise par Claude.

Franck, le 10/11/2026 : « j'aimerais pouvoir proposer des corrections dans une boîte de
dialogue IA ». La case de correction ne connaissait qu'une liste de tournures apprises
par cœur ; « accorde au masculin » ou « c'est lourd, allège » lui passaient au-dessus.

Claude **ne corrige rien lui-même**. Il lit la demande et dit de quelle nature elle est :

- le **dossier clinique** : il la traduit en opérations de correction — les mêmes que
  celles de l'écran, validées par le même code, appliquées par le même chemin ;
- la **rédaction** : il en tire une consigne de forme, que le rédacteur suivra sous ses
  garde-fous habituels (aucun fait ajouté, retiré ni modifié) ;
- la **civilité** du patient ;
- ou il n'a pas compris, et pose sa question.

Rien n'est appliqué ici : la lecture revient au praticien, qui confirme.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Literal, get_args

import httpx
from pydantic import TypeAdapter, ValidationError

from oris_api.contracts import ClinicalEncounter
from oris_api.contracts.generated import (
    ClinicalFactAssertion,
    ClinicalFactCategory,
    ClinicalFactCertainty,
    ClinicalFactClinicalStatus,
    ClinicalFactTemporality,
    TreatmentPlanItemStatus,
)
from oris_api.domain.corrections import (
    AddFact,
    CorrectionOperation,
    RemoveFact,
    ReplaceTooth,
    SetPlanItemStatus,
    UpdateFact,
)

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"
PROMPT_VERSION = "assistant-fr-3"
MAX_TOKENS = 3_000
PROPOSITIONS_MAX = 5

Nature = Literal["dossier", "redaction", "civilite", "incompris"]

#: Ce que le dialogue a le droit de demander au dossier. Réordonner ou vider un plan se
#: fait à l'écran, où l'on voit ce qu'on déplace.
PERMISES = (ReplaceTooth, UpdateFact, RemoveFact, SetPlanItemStatus, AddFact)
OPERATIONS: TypeAdapter[list[CorrectionOperation]] = TypeAdapter(list[CorrectionOperation])

COMPRENDRE_PROMPT = """Tu assistes un chirurgien-dentiste français qui relit le compte rendu \
qu'Oris a rédigé après sa consultation. Il t'écrit une demande de correction en langage \
courant. Tu ne corriges rien toi-même : tu dis ce que tu as compris, et Oris appliquera \
après son accord.

Classe la demande (`nature`) :
- `redaction` — elle porte sur la FORME du texte : ton, longueur, tournures, répétitions, \
ordre des phrases, regroupements, vocabulaire. Écris alors dans `consigne` une instruction \
courte à l'infinitif pour le rédacteur, réutilisable telle quelle sur un autre patient \
(« Attribuer les propos du patient une seule fois par paragraphe », « Faire des phrases \
courtes »). Aucun fait clinique ne doit y figurer.
- `civilite` — elle dit que le patient est un homme ou une femme (« c'est un patient, pas \
une patiente », « accorde au féminin »). Renseigne `civilite`.
- `dossier` — elle change un FAIT clinique : une dent, un âge, un statut, une décision, un \
constat à retirer, une information que le praticien ajoute. Traduis-la en `operations`, \
avec les identifiants (`fact_id`, `item_id`) pris dans le dossier fourni, jamais inventés, \
et les noms de champs du dossier, tels quels : `value`, `teeth`, `clinical_status`… \
Pour changer ce qu'un fait dit, c'est `update_fact` avec `changes.value` (la phrase \
entière, corrigée). Pour une dent, `replace_tooth` ; limite-le à certains faits avec \
`fact_ids`. Un fait dit par le patient garde `clinical_status: patient_reported`.
- `incompris` — tu ne sais pas ce qu'il faut changer, ou plusieurs cibles sont possibles. \
Pose ta question dans `question`. C'est toujours mieux que de deviner.

Règles absolues :
- n'invente rien : une opération `add_fact` ne contient que ce que le praticien vient \
d'écrire, avec ses mots ;
- une demande de forme ne devient jamais une opération sur le dossier, et inversement ;
- `resume` est une phrase adressée au praticien, en français simple, qui dit ce que tu as \
compris et ce qui va changer — sans jargon informatique, sans identifiant. Écris-la au \
FUTUR (« Je vais remplacer… », « Le compte rendu sera accordé… ») : rien n'est encore \
fait, le praticien doit d'abord confirmer. N'écris jamais « j'ai corrigé »."""

RELIRE_PROMPT = """Tu relis un document dentaire rédigé pour un chirurgien-dentiste \
français, et tu proposes des améliorations de FORME : lourdeurs, répétitions, paragraphes \
à regrouper, phrases trop longues, ordre peu clair, formules creuses. Tu ne proposes \
jamais de changer un fait, une dent, un chiffre, une négation, une incertitude ou un \
refus : le fond appartient au praticien.

Rends au plus cinq propositions, les plus utiles d'abord. Pour chacune : un `titre` de \
trois à sept mots, un `detail` d'une phrase qui dit où et quoi, et la `consigne` à donner \
au rédacteur, à l'infinitif. Si le document se lit déjà bien, rends une liste vide : ne \
propose rien pour proposer. Ne répète pas une consigne déjà en vigueur."""


class AssistantIndisponible(RuntimeError):
    """Le service d'IA n'a pas répondu, ou a refusé : le code dit pourquoi."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class Lecture:
    """Ce que Claude a compris de la demande. Rien n'est encore appliqué."""

    nature: Nature
    resume: str
    consigne: str = ""
    civilite: str = ""
    operations: list[CorrectionOperation] = field(default_factory=list)
    question: str = ""


@dataclass(frozen=True)
class Proposition:
    titre: str
    detail: str
    consigne: str


def _valeurs(literal: Any) -> list[str]:
    return [str(v) for v in get_args(literal)]


def comprendre_schema() -> dict[str, Any]:
    dent = {"type": "string", "description": "Numéro FDI, par exemple « 26 »."}
    axes = {
        "assertion": {"type": "string", "enum": _valeurs(ClinicalFactAssertion)},
        "temporality": {"type": "string", "enum": _valeurs(ClinicalFactTemporality)},
        "clinical_status": {"type": "string", "enum": _valeurs(ClinicalFactClinicalStatus)},
        "certainty": {"type": "string", "enum": _valeurs(ClinicalFactCertainty)},
        "teeth": {"type": "array", "items": dent},
        "value": {"description": "Ce qui est dit, avec les mots du praticien."},
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["nature", "resume"],
        "properties": {
            "nature": {"type": "string", "enum": ["dossier", "redaction", "civilite", "incompris"]},
            "resume": {"type": "string"},
            "consigne": {"type": "string"},
            "civilite": {"type": "string", "enum": ["monsieur", "madame"]},
            "question": {"type": "string"},
            "operations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["operation"],
                    "properties": {
                        "operation": {
                            "type": "string",
                            "enum": [
                                "replace_tooth",
                                "update_fact",
                                "remove_fact",
                                "set_plan_item_status",
                                "add_fact",
                            ],
                        },
                        "from_tooth": dent,
                        "to_tooth": dent,
                        "fact_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "replace_tooth : les faits visés ; omis, tous.",
                        },
                        "fact_id": {
                            "type": "string",
                            "description": "update_fact, remove_fact : le fait visé.",
                        },
                        "item_id": {"type": "string"},
                        "status": {"type": "string", "enum": _valeurs(TreatmentPlanItemStatus)},
                        "changes": {
                            "type": "object",
                            "additionalProperties": False,
                            "description": "update_fact : seulement les champs qui changent.",
                            "properties": axes,
                        },
                        "fact": {
                            "type": "object",
                            "additionalProperties": False,
                            "description": "add_fact : le fait que le praticien vient de dire.",
                            "required": ["category", "concept", "value", "clinical_status"],
                            "properties": {
                                "category": {
                                    "type": "string",
                                    "enum": _valeurs(ClinicalFactCategory),
                                },
                                "concept": {
                                    "type": "string",
                                    "description": "Identifiant court en anglais, comme ceux "
                                    "du dossier (« allergy », « pain »).",
                                },
                                **axes,
                            },
                        },
                    },
                },
            },
        },
    }


def relire_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["propositions"],
        "properties": {
            "propositions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["titre", "detail", "consigne"],
                    "properties": {
                        "titre": {"type": "string"},
                        "detail": {"type": "string"},
                        "consigne": {"type": "string"},
                    },
                },
            }
        },
    }


def dossier_pour_claude(obj: ClinicalEncounter) -> dict[str, Any]:
    """Le dossier tel que Claude le voit : des faits, jamais le nom du patient.

    Les champs portent **les noms du contrat** (`value`, `teeth`, `clinical_status`…) :
    Claude réemploie dans ses opérations les mots qu'il a sous les yeux. Montrés en
    français (« valeur », « dents »), il les rendait en français, et Oris rejetait trois
    corrections sur quatre qu'il avait pourtant comprises (Franck, 10/11/2026 : « il a
    compris mais pas réalisé »).
    """
    plan = obj.treatment_plan
    return {
        "facts": [
            {
                "fact_id": f.fact_id,
                "category": f.category,
                "concept": f.concept,
                "value": f.value,
                "teeth": list(f.teeth),
                "assertion": f.assertion,
                "clinical_status": f.clinical_status,
                "temporality": f.temporality,
                "certainty": f.certainty,
            }
            for f in obj.facts
        ],
        "plan_items": [
            {"item_id": i.item_id, "action": i.action, "teeth": list(i.teeth), "status": i.status}
            for i in (plan.items if plan else [])
        ],
    }


#: Ce que Claude écrit parfois à la place des noms du contrat. On le remet d'aplomb
#: plutôt que de rejeter une correction comprise pour un nom de champ.
SYNONYMES = {
    "valeur": "value",
    "dents": "teeth",
    "rubrique": "category",
    "categorie": "category",
    "statut": "clinical_status",
    "temporalite": "temporality",
    "certitude": "certainty",
}
CHAMPS_CHANGES = {"assertion", "temporality", "clinical_status", "certainty", "teeth", "value"}
CHAMPS_FAIT = {
    "category",
    "concept",
    "value",
    "teeth",
    "surfaces",
    "assertion",
    "temporality",
    "clinical_status",
    "certainty",
}


def _contrat(objet: Any, permis: set[str]) -> dict[str, Any]:
    if not isinstance(objet, dict):
        return {}
    propre = {SYNONYMES.get(str(cle), str(cle)): valeur for cle, valeur in objet.items()}
    return {cle: valeur for cle, valeur in propre.items() if cle in permis}


def normaliser(operations: Any) -> list[dict[str, Any]]:
    """Remet les opérations de Claude à la forme du contrat, sans rien y ajouter."""
    propres: list[dict[str, Any]] = []
    for brute in operations if isinstance(operations, list) else []:
        if not isinstance(brute, dict):
            continue
        nom = brute.get("operation")
        if nom == "replace_tooth":
            operation: dict[str, Any] = {
                "operation": nom,
                "from_tooth": str(brute.get("from_tooth", "")),
                "to_tooth": str(brute.get("to_tooth", "")),
            }
            cibles = brute.get("fact_ids") or ([brute["fact_id"]] if brute.get("fact_id") else None)
            if cibles:
                operation["fact_ids"] = [str(c) for c in cibles]
        elif nom == "update_fact":
            operation = {
                "operation": nom,
                "fact_id": str(brute.get("fact_id", "")),
                "changes": _contrat(brute.get("changes"), CHAMPS_CHANGES),
            }
        elif nom == "remove_fact":
            operation = {"operation": nom, "fact_id": str(brute.get("fact_id", ""))}
        elif nom == "set_plan_item_status":
            operation = {
                "operation": nom,
                "item_id": str(brute.get("item_id", "")),
                "status": brute.get("status"),
            }
        elif nom == "add_fact":
            fait = _contrat(brute.get("fact"), CHAMPS_FAIT)
            fait.setdefault("teeth", [])
            fait.setdefault("assertion", "present")
            fait.setdefault("temporality", "current")
            fait.setdefault("certainty", "certain")
            operation = {"operation": nom, "fact": fait}
        else:
            operation = dict(brute)
        propres.append(operation)
    return propres


def lire(sortie: dict[str, Any], obj: ClinicalEncounter) -> Lecture:
    """Contrôle la réponse de Claude. Ce qui ne tient pas debout redevient une question."""
    nature = sortie.get("nature")
    resume = str(sortie.get("resume") or "").strip()
    if nature == "redaction":
        consigne = " ".join(str(sortie.get("consigne") or "").split())
        if len(consigne) < 3:
            return _incompris("Je n'ai pas su tirer une consigne de rédaction de cette demande.")
        return Lecture("redaction", resume, consigne=consigne[:240])
    if nature == "civilite":
        civilite = sortie.get("civilite")
        if civilite not in {"monsieur", "madame"}:
            return _incompris("Dites-moi s'il s'agit d'un homme ou d'une femme.")
        return Lecture("civilite", resume, civilite=str(civilite))
    if nature == "dossier":
        try:
            operations = OPERATIONS.validate_python(normaliser(sortie.get("operations")))
        except ValidationError:
            return _incompris(
                "J'ai compris qu'il fallait corriger le dossier, mais pas précisément quoi. "
                "Reformulez en nommant la dent ou le fait."
            )
        if not operations or not all(isinstance(o, PERMISES) for o in operations):
            return _incompris("Cette correction se fait dans « Données cliniques ».")
        faits = {f.fact_id for f in obj.facts}
        elements = {i.item_id for i in (obj.treatment_plan.items if obj.treatment_plan else [])}
        for operation in operations:
            cible = getattr(operation, "fact_id", None)
            if cible is not None and cible not in faits:
                return _incompris("Je n'ai pas retrouvé ce fait dans le dossier. Lequel est-ce ?")
            element = getattr(operation, "item_id", None)
            if element is not None and element not in elements:
                return _incompris("Je n'ai pas retrouvé cette étape dans le plan. Laquelle ?")
        return Lecture("dossier", resume, operations=operations)
    question = str(sortie.get("question") or resume).strip()
    return _incompris(question or "Je n'ai pas compris ce qu'il faut changer.")


def _incompris(question: str) -> Lecture:
    return Lecture("incompris", question, question=question)


class AssistantCorrections:
    """Comprendre une demande de correction, et relire un document."""

    def __init__(
        self,
        api_key: str,
        model: str,
        client: httpx.AsyncClient | None = None,
        timeout_s: float = 60,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._client = client
        self._timeout = timeout_s
        self.version = f"{model}/{PROMPT_VERSION}"

    async def comprendre(self, demande: str, obj: ClinicalEncounter, civilite: str = "") -> Lecture:
        contenu = json.dumps(
            {
                "demande": demande,
                "civilite_connue": civilite or "non précisée",
                "dossier": dossier_pour_claude(obj),
            },
            ensure_ascii=False,
        )
        sortie = await self._appeler(
            COMPRENDRE_PROMPT,
            contenu,
            (
                "comprendre_la_demande",
                "Dit ce que la demande du praticien change.",
                comprendre_schema(),
            ),
        )
        return lire(sortie, obj)

    async def relire(
        self, document_type: str, rubriques: list[dict[str, str]], consignes: list[str]
    ) -> list[Proposition]:
        contenu = json.dumps(
            {"document": document_type, "consignes_en_vigueur": consignes, "rubriques": rubriques},
            ensure_ascii=False,
        )
        sortie = await self._appeler(
            RELIRE_PROMPT,
            contenu,
            ("proposer_des_ameliorations", "Propose des améliorations de forme.", relire_schema()),
        )
        propositions: list[Proposition] = []
        for brute in sortie.get("propositions") or []:
            titre = " ".join(str(brute.get("titre") or "").split())
            consigne = " ".join(str(brute.get("consigne") or "").split())
            if titre and len(consigne) >= 3:
                detail = " ".join(str(brute.get("detail") or "").split())
                propositions.append(Proposition(titre[:80], detail[:240], consigne[:240]))
        return propositions[:PROPOSITIONS_MAX]

    async def _appeler(
        self, system: str, contenu: str, tool: tuple[str, str, dict[str, Any]]
    ) -> dict[str, Any]:
        nom, description, schema = tool
        client = self._client or httpx.AsyncClient(timeout=self._timeout)
        try:
            response = await client.post(
                API_URL,
                headers={
                    "x-api-key": self._api_key,
                    "anthropic-version": API_VERSION,
                    "content-type": "application/json",
                },
                json={
                    "model": self._model,
                    "max_tokens": MAX_TOKENS,
                    "system": system,
                    "messages": [{"role": "user", "content": contenu}],
                    "tools": [{"name": nom, "description": description, "input_schema": schema}],
                    "tool_choice": {"type": "tool", "name": nom},
                },
            )
        except httpx.TimeoutException as error:
            raise AssistantIndisponible("ANTHROPIC_TIMEOUT") from error
        except httpx.HTTPError as error:
            raise AssistantIndisponible("ANTHROPIC_NETWORK") from error
        finally:
            if self._client is None:
                await client.aclose()
        if response.status_code in {401, 403}:
            raise AssistantIndisponible("ANTHROPIC_AUTH")
        if response.status_code == 429 or response.status_code >= 500:
            raise AssistantIndisponible(f"ANTHROPIC_HTTP_{response.status_code}")
        if response.status_code >= 400:
            raise AssistantIndisponible(f"ANTHROPIC_REJECTED_{response.status_code}")
        for block in response.json().get("content") or []:
            if block.get("type") == "tool_use" and block.get("name") == nom:
                return dict(block.get("input") or {})
        raise AssistantIndisponible("ANTHROPIC_REJECTED_200")
