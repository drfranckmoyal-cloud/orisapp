"""Glossaire dentaire transmis aux fournisseurs STT (phrase list / keyterms).

Aide la reconnaissance, n'ajoute jamais de fait (CLAUDE.md, apprentissage). Limité à
50 termes : au-delà, Deepgram dégrade ses résultats (500 jetons maximum par requête).
"""

from __future__ import annotations

DENTAL_GLOSSARY_FR: tuple[str, ...] = (
    # Matériaux et marques du corpus
    "Filtek Supreme XTE",
    "G-ænial A'CHORD",
    "Clearfil Majesty ES-2",
    "Essentia",
    "Scotchbond Universal Plus",
    "Clearfil Universal Bond Quick",
    "G-Premio BOND",
    "Variolink Esthetic",
    "RelyX Veneer",
    "G-CEM Veneer",
    "Eliquis",
    # Dictés par le praticien le 19/09 : marques et sigles que la transcription rate
    "Astéria",
    "SmileCloud",
    "peroxyde de carbamide",
    "zircone",
    "DVO",
    # Actes et examens
    "composite",
    "composites additifs",
    "facettes céramiques",
    "mock-up",
    "digue",
    "mordançage",
    "adhésif",
    "empreinte optique",
    "provisoires",
    "avulsion",
    "ostéotomie",
    "lambeau",
    "hémostase",
    "sutures",
    "anesthésie locale",
    "blanchiment",
    "polissage",
    # Constats et diagnostics
    "diastème",
    "usure",
    "érosion",
    "bruxisme",
    "fissure",
    "carie",
    "hypersensibilité",
    "restauration fracturée",
    "réévaluation",
    # Surfaces
    "mésiale",
    "distale",
    "occlusale",
    "vestibulaire",
    "palatine",
    "linguale",
    "incisale",
    "cervicale",
)

assert len(DENTAL_GLOSSARY_FR) <= 50  # noqa: S101 - garde-fou de configuration
