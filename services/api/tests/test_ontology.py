"""Vocabulaire clinique : cohérence des thèmes et liste du praticien à jour."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

from oris_api.contracts import ClinicalFact
from oris_api.documents.renderer import UNRENDERED_PREFIX, fact_sentence
from oris_api.ontology.labels import CONCEPTS, THEMES, ValueMode

ROOT = Path(__file__).resolve().parents[3]
MODES: set[ValueMode] = {"hide", "show", "value_only", "statement"}


def test_every_concept_belongs_to_exactly_one_theme() -> None:
    placed = [concept for group in THEMES.values() for concept in group]
    assert len(placed) == len(set(placed)) == len(CONCEPTS)


def test_labels_are_french_sentences_ready() -> None:
    for concept, label in CONCEPTS.items():
        assert label.label.strip() == label.label and label.label, concept
        assert label.label[0].islower() or label.label[0].isupper(), concept
        assert label.value_mode in MODES, concept
        # Un libellé n'est pas un code : il doit se lire.
        assert "_" not in label.label, concept


def test_a_known_concept_is_written_and_an_unknown_one_is_flagged() -> None:
    def fact(concept: str) -> ClinicalFact:
        return ClinicalFact.model_validate(
            {
                "fact_id": "f1",
                "category": "clinical_finding",
                "concept": concept,
                "value": "présente",
                "teeth": ["16"],
                "surfaces": [],
                "assertion": "present",
                "temporality": "current",
                "clinical_status": "observed",
                "speaker_role": "practitioner",
                "certainty": "certain",
                "source_type": "audio",
                "evidence_segment_ids": ["t1"],
                "manually_validated": False,
                "confidence": 0.9,
            }
        )

    # « crowns » manquait : le compte rendu affichait « à rédiger ».
    assert "couronnes" in fact_sentence(fact("crowns"))
    assert fact_sentence(fact("licorne_dentaire")).startswith(UNRENDERED_PREFIX)


def vocabulaire() -> Any:
    spec = importlib.util.spec_from_file_location("vocabulaire", ROOT / "scripts/vocabulaire.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["vocabulaire"] = module
    spec.loader.exec_module(module)
    return module


def test_practitioner_vocabulary_list_is_up_to_date() -> None:
    """`docs/VOCABULAIRE.md` est produit depuis le code : il ne doit pas dériver.

    Les ajouts écrits par le praticien dans les tableaux « À ajouter » sont ignorés :
    seuls les termes déjà connus d'Oris doivent correspondre.
    """
    module = vocabulaire()
    published = module.TARGET.read_text(encoding="utf-8")
    assert module.known_terms(published) == module.known_terms(module.render())


def test_vocabulary_script_lists_every_theme() -> None:
    rendered = vocabulaire().render()
    for theme in THEMES:
        assert f"## {theme}" in rendered
    assert rendered.count("**À ajouter dans ce thème**") == len(THEMES)
