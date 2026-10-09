"""Fabrique le son que fait Oris quand l'écoute se coupe.

Trois notes qui descendent, répétées deux fois, en timbre un peu rude : rien dans
l'iPhone ne sonne comme ça, et c'est le but — le praticien doit le reconnaître sans
regarder son téléphone, au milieu du bruit d'un cabinet. Le site joue le même motif,
fabriqué à la volée par `apps/web/src/lib/audio/alerte.ts` : les deux doivent rester
d'accord.

    python3 scripts/fabriquer-son-alerte.py
"""

from __future__ import annotations

import math
import struct
import wave
from pathlib import Path

TAUX = 44_100
NOTES = [(988.0, 0.16), (740.0, 0.16), (554.0, 0.30)]  # si5, fa#5, do#5 : une chute nette
SILENCE_ENTRE_NOTES = 0.04
SILENCE_ENTRE_MOTIFS = 0.18
REPETITIONS = 2
SORTIE = Path(__file__).resolve().parent.parent / "apps/ios/Oris/Resources/ecoute-coupee.wav"


def note(frequence: float, duree: float) -> list[float]:
    sortie = []
    for i in range(int(TAUX * duree)):
        t = i / TAUX
        # Fondamentale + quinte + une pointe d'harmonique impaire : timbre franc, un peu
        # métallique, qui perce une pièce bruyante sans être strident.
        onde = (
            math.sin(2 * math.pi * frequence * t)
            + 0.45 * math.sin(2 * math.pi * frequence * 1.5 * t)
            + 0.18 * math.sin(2 * math.pi * frequence * 3 * t)
        )
        # Attaque immédiate, extinction douce : on l'entend commencer, pas claquer.
        montee = min(1.0, t / 0.006)
        chute = min(1.0, (duree - t) / 0.05)
        sortie.append(onde * montee * chute / 1.63)
    return sortie


def main() -> None:
    echantillons: list[float] = []
    for repetition in range(REPETITIONS):
        for frequence, duree in NOTES:
            echantillons += note(frequence, duree) + [0.0] * int(TAUX * SILENCE_ENTRE_NOTES)
        if repetition < REPETITIONS - 1:
            echantillons += [0.0] * int(TAUX * SILENCE_ENTRE_MOTIFS)

    with wave.open(str(SORTIE), "wb") as fichier:
        fichier.setnchannels(1)
        fichier.setsampwidth(2)
        fichier.setframerate(TAUX)
        fichier.writeframes(
            b"".join(
                struct.pack("<h", int(max(-1.0, min(1.0, v)) * 30_000)) for v in echantillons
            )
        )
    print(f"{SORTIE.name} : {len(echantillons) / TAUX:.2f} s")


if __name__ == "__main__":
    main()
