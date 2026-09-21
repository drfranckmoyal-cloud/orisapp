"""Reconnaître le même patient sous deux orthographes — et refuser de trancher sinon.

Ces cas ne sont pas inventés : ils viennent des agendas Doctolib et des dossiers
SmileCloud du cabinet. Le plus important est le dernier groupe — ce que le
rapprochement **refuse** de décider tout seul.
"""

from __future__ import annotations

import pytest

from oris_api.services.rapprochement import DOUTE, SUR, proposer, ressemblance


@pytest.mark.parametrize(
    "a, b",
    [
        ("Chloé MOREAU", "Moreau Chloe"),  # accents, casse, ordre inversé
        ("Éric URBAN", "eric urban"),
        ("Claire DA SILVA", "DA SILVA Claire"),
        ("Jean-Pierre MARTIN", "jean pierre martin"),  # le trait d'union n'est pas un mot
        ("  Marie   DESFRAY ", "Marie DESFRAY"),  # espaces en trop
    ],
)
def test_le_meme_nom_ecrit_autrement_vaut_certitude(a: str, b: str) -> None:
    assert ressemblance(a, b) >= SUR


def test_un_nom_colle_reste_le_meme_nom() -> None:
    """« DA SILVA » et « DASILVA » : une espace en moins, pas un autre patient."""
    assert ressemblance("Claire DA SILVA", "Claire DASILVA") >= DOUTE


@pytest.mark.parametrize(
    "a, b",
    [
        ("Paul MARTIN", "Paule MARTIN"),  # une lettre, deux personnes
        ("Jean DUPONT", "Jean DUPOND"),
        ("Marie DESFRAY", "Marie DESFRAYE"),
    ],
)
def test_une_lettre_de_difference_ne_fait_jamais_une_certitude(a: str, b: str) -> None:
    """Le cœur de la règle : ça se ressemble, donc on demande — on ne décide pas."""
    note = ressemblance(a, b)
    assert DOUTE <= note < SUR


def test_deux_patients_sans_rapport_ne_se_ressemblent_pas() -> None:
    assert ressemblance("Chloé MOREAU", "Éric URBAN") < DOUTE


def test_un_nom_vide_ne_ressemble_a_rien() -> None:
    assert ressemblance("", "Chloé MOREAU") == 0.0
    assert ressemblance("Chloé MOREAU", "   ") == 0.0


def test_un_mot_manquant_coute_cher() -> None:
    """« Anne Marie DUBOIS » n'est pas « Anne DUBOIS » : un prénom de plus compte."""
    assert ressemblance("Anne Marie DUBOIS", "Anne DUBOIS") < SUR


def test_un_mot_ne_sert_qu_une_fois() -> None:
    """Sans cette règle, « Jean Jean » ressemblerait parfaitement à « Jean Dupont »."""
    assert ressemblance("Jean Jean", "Jean Dupont") < DOUTE


# --- Ce que le rapprochement propose, face à une liste de noms connus ---

CONNUS = [
    ("p1", "Chloé MOREAU"),
    ("p2", "Éric URBAN"),
    ("p3", "Paul MARTIN"),
]


def test_un_correspondant_certain_est_trouve() -> None:
    propose = proposer("Moreau Chloe", CONNUS)
    assert propose.etat == "trouve"
    assert propose.certain
    assert propose.cle == "p1"


def test_un_nom_qui_ressemble_demande_confirmation() -> None:
    propose = proposer("Paule MARTIN", CONNUS)
    assert propose.etat == "a_confirmer"
    assert not propose.certain
    assert propose.cle is None
    assert [c.cle for c in propose.candidats] == ["p3"]
    assert 72 <= propose.candidats[0].pour_cent < 100


def test_deux_homonymes_certains_ne_se_tranchent_pas_au_hasard() -> None:
    """Le même nom sur deux dossiers : on ne choisit pas, on montre les deux."""
    propose = proposer("Paul MARTIN", [("p3", "Paul MARTIN"), ("p4", "Paul Martin")])
    assert propose.etat == "ambigu"
    assert not propose.certain
    assert propose.cle is None
    assert len(propose.candidats) == 2


def test_un_inconnu_est_declare_absent() -> None:
    propose = proposer("Salima CHIKHAOUI", CONNUS)
    assert propose.etat == "absent"
    assert propose.candidats == ()
    assert propose.cle is None


def test_les_candidats_viennent_du_plus_ressemblant_au_moins() -> None:
    propose = proposer(
        "Jean DUPONT", [("a", "Jean DUPOND"), ("b", "Jeanne DUPONTEL"), ("c", "Jean DUPONTT")]
    )
    pour_cents = [c.pour_cent for c in propose.candidats]
    assert pour_cents == sorted(pour_cents, reverse=True)


def test_une_liste_vide_ne_trouve_rien() -> None:
    assert proposer("Chloé MOREAU", []).etat == "absent"
