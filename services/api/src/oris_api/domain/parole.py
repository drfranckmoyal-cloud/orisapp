"""« Est-ce que ça a vraiment parlé ? » — mesure de la parole d'une consultation.

Sert à distinguer les deux visages d'un résultat vide : une consultation qui n'avait
rien à dire (un essai de trente secondes, une consultation annulée) et une extraction
qui a échoué sans le dire. Le 09/10/2026, trente-trois minutes de parole clinique
(250 passages, 3 000 mots) sont ressorties avec zéro fait, et Oris l'a présentée au
praticien comme un dossier « à relire » : d'où ce seuil, lu à deux endroits — par
l'extraction, qui refuse un vide suspect, et par le pipeline, qui accepte de reprendre
une consultation déjà rangée mais vide.
"""

from __future__ import annotations

from collections.abc import Sequence

from oris_api.contracts import TranscriptSegment

#: En deçà, une consultation peut légitimement ne rien contenir de clinique.
#: Au-delà, un résultat vide est une panne à signaler.
MIN_PASSAGES_PARLES = 20
MIN_MOTS_PARLES = 150


def parole_consistante(segments: Sequence[TranscriptSegment]) -> bool:
    """La consultation a-t-elle assez parlé pour qu'un résultat vide soit suspect ?"""
    dits = [s for s in segments if s.text.strip()]
    mots = sum(len(s.text.split()) for s in dits)
    return len(dits) >= MIN_PASSAGES_PARLES and mots >= MIN_MOTS_PARLES
