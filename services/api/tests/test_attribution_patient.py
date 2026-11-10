"""« Selon le patient » : une fois par suite de phrases, pas à chacune.

Franck, le 10/11/2026, sur un compte rendu réel : quarante « Selon le patient » pour
cinquante-quatre phrases — « beaucoup de lourdeur ». L'invariant clinique ne bouge pas :
on distingue toujours ce que le patient rapporte de ce que le praticien constate. Ce qui
change, c'est qu'on ne le redit plus à chaque ligne.
"""

from __future__ import annotations

from typing import Any

import pytest

from oris_api.contracts import ClinicalFact
from oris_api.documents.renderer import Style, alleger_attribution, selon
from oris_api.domain.types import Claim
from oris_api.llm.redaction import RedactionRefusee, Rubrique, verifier


def fait(fact_id: str, statut: str, valeur: str = "douleur") -> ClinicalFact:
    return ClinicalFact.model_validate(
        {
            "fact_id": fact_id,
            "category": "symptom",
            "concept": "pain",
            "value": valeur,
            "teeth": [],
            "surfaces": [],
            "assertion": "present",
            "temporality": "current",
            "clinical_status": statut,
            "speaker_role": "patient",
            "certainty": "certain",
            "source_type": "audio",
            "confidence": 0.9,
            "evidence_segment_ids": [],
            "manually_validated": False,
        }
    )


STATUTS = {
    "p1": "patient_reported",
    "p2": "patient_reported",
    "p3": "patient_reported",
    "o1": "observed",
}


def test_le_gabarit_ne_repete_plus_la_formule() -> None:
    claims = [
        Claim("Motif", "Selon le patient, mal à la mâchoire.", fact_ids=("p1",)),
        Claim("Motif", "Selon le patient, mal aux tempes.", fact_ids=("p2",)),
        Claim("Motif", "Selon le patient, dort mal.", fact_ids=("p3",)),
    ]
    textes = [c.text for c in alleger_attribution(claims, STATUTS)]
    assert textes == ["Selon le patient, mal à la mâchoire.", "Mal aux tempes.", "Dort mal."]


def test_un_constat_du_praticien_ferme_la_suite() -> None:
    """Après un constat, la parole du patient redit d'où elle vient : c'est l'invariant."""
    claims = [
        Claim("Examen", "Selon le patient, mal à la mâchoire.", fact_ids=("p1",)),
        Claim("Examen", "Constaté : usure des incisives.", fact_ids=("o1",)),
        Claim("Examen", "Selon le patient, mal aux tempes.", fact_ids=("p2",)),
    ]
    textes = [c.text for c in alleger_attribution(claims, STATUTS)]
    assert textes[2] == "Selon le patient, mal aux tempes."


def test_la_formule_s_accorde_a_la_civilite() -> None:
    assert selon(Style(civilite="madame")) == "Selon la patiente, "
    assert selon(Style()) == "Selon le patient, "
    claims = [
        Claim("Motif", "Selon la patiente, mal à la mâchoire.", fact_ids=("p1",)),
        Claim("Motif", "Selon la patiente, mal aux tempes.", fact_ids=("p2",)),
    ]
    assert alleger_attribution(claims, STATUTS)[1].text == "Mal aux tempes."


def copie(*phrases: dict[str, Any]) -> dict[str, Any]:
    return {"rubriques": [{"titre": "Motif", "phrases": list(phrases)}]}


def rubrique(*ids: str) -> list[Rubrique]:
    return [Rubrique("Motif", tuple(Claim("Motif", "…", fact_ids=(i,)) for i in ids))]


def test_la_copie_de_claude_attribue_une_fois_par_paragraphe() -> None:
    faits = {"p1": fait("p1", "patient_reported"), "p2": fait("p2", "patient_reported")}
    acceptee = copie(
        {"texte": "La patiente rapporte une douleur.", "fact_ids": ["p1"]},
        {"texte": "Une douleur gêne aussi le sommeil.", "fact_ids": ["p2"]},
    )
    assert len(verifier(rubrique("p1", "p2"), acceptee, faits)) == 2


def test_une_parole_du_patient_sans_attribution_est_refusee() -> None:
    faits = {"p1": fait("p1", "patient_reported")}
    with pytest.raises(RedactionRefusee, match="attribution au patient perdue"):
        verifier(
            rubrique("p1"),
            copie({"texte": "Une douleur est présente.", "fact_ids": ["p1"]}),
            faits,
        )


def test_un_nouveau_paragraphe_redit_la_source() -> None:
    faits = {"p1": fait("p1", "patient_reported"), "p2": fait("p2", "patient_reported")}
    sans = copie(
        {"texte": "Elle décrit une douleur.", "fact_ids": ["p1"]},
        {"texte": "Une douleur gêne le sommeil.", "fact_ids": ["p2"], "nouveau_paragraphe": True},
    )
    with pytest.raises(RedactionRefusee, match="attribution au patient perdue"):
        verifier(rubrique("p1", "p2"), sans, faits)


def test_selon_le_patient_deux_fois_dans_une_rubrique_est_refuse() -> None:
    faits = {"p1": fait("p1", "patient_reported"), "p2": fait("p2", "patient_reported")}
    lourde = copie(
        {"texte": "Selon le patient, une douleur.", "fact_ids": ["p1"]},
        {"texte": "Selon le patient, une douleur la nuit.", "fact_ids": ["p2"]},
    )
    with pytest.raises(RedactionRefusee, match="répété"):
        verifier(rubrique("p1", "p2"), lourde, faits)
