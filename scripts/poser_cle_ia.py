"""Pose la clé Anthropic dans `services/api/.env`, après l'avoir essayée.

La clé est demandée sans être affichée, essayée contre l'API, et **n'est écrite que si
Anthropic l'accepte** : une clé fausse ne remplace jamais celle qui est en place. Elle
n'apparaît ni à l'écran, ni dans l'historique du terminal, ni dans un message.

    python3 scripts/poser_cle_ia.py
    grep ^ANTHROPIC_API_KEY= services/api/.env | ssh … poser_cle_ia.py --depuis-entree

La seconde forme recopie la clé d'un poste vers un autre (le Mac vers le serveur en
ligne) : Anthropic ne montre une clé qu'une fois, et personne ne la retient. Elle passe
par l'entrée standard, jamais par la ligne de commande, que `ps` afficherait.
"""

from __future__ import annotations

import argparse
import getpass
import json
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path

ENV = Path(__file__).resolve().parent.parent / "services" / "api" / ".env"
VARIABLE = "ANTHROPIC_API_KEY"


def confiance() -> ssl.SSLContext:
    """Les autorités de certification, prises là où elles se trouvent.

    Le Python livré avec macOS n'en a pas installé : sans ça, tout appel en https
    échoue sur « certificate verify failed » et on croirait la clé fausse.
    """
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def essayer(cle: str) -> tuple[bool, str]:
    """Un appel minuscule : la clé passe, ou Anthropic dit pourquoi elle ne passe pas."""
    requete = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(
            {
                "model": "claude-sonnet-4-5",
                "max_tokens": 16,
                "messages": [{"role": "user", "content": "bonjour"}],
            }
        ).encode(),
        headers={
            "x-api-key": cle,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(requete, timeout=60, context=confiance()) as reponse:
            return reponse.status == 200, "acceptée"
    except urllib.error.HTTPError as refus:
        corps = refus.read().decode(errors="replace")
        try:
            motif = json.loads(corps)["error"]["message"]
        except Exception:  # noqa: BLE001 - un corps illisible se lit tel quel
            motif = corps[:200]
        return False, f"{refus.code} — {motif}"
    except Exception as panne:  # noqa: BLE001 - réseau coupé, proxy, DNS…
        return False, f"appel impossible : {panne}"


def remplacer(texte: str, cle: str) -> str:
    lignes = texte.splitlines()
    for rang, ligne in enumerate(lignes):
        if ligne.startswith(f"{VARIABLE}="):
            lignes[rang] = f"{VARIABLE}={cle}"
            break
    else:
        lignes.append(f"{VARIABLE}={cle}")
    return "\n".join(lignes) + "\n"


def lire(depuis_entree: bool) -> str:
    """La clé, tapée à l'abri des regards ou reçue d'un autre poste par l'entrée standard."""
    if not depuis_entree:
        return getpass.getpass("Clé Anthropic (elle ne s'affiche pas) : ").strip()
    # On accepte la clé seule ou la ligne entière du fichier, « ANTHROPIC_API_KEY=… » :
    # c'est ce que rend un `grep` sur le .env de l'autre poste.
    brut = sys.stdin.read().strip()
    return brut.split("=", 1)[1].strip() if brut.startswith(f"{VARIABLE}=") else brut


def main() -> int:
    arguments = argparse.ArgumentParser(description=__doc__)
    arguments.add_argument(
        "--depuis-entree",
        action="store_true",
        help="lire la clé sur l'entrée standard au lieu de la demander",
    )
    options = arguments.parse_args()

    if not ENV.exists():
        print(f"Pas de fichier {ENV} : rien à modifier.")
        return 1

    cle = lire(options.depuis_entree)
    if not cle:
        print("Rien saisi : le fichier n'a pas été touché.")
        return 1
    if not cle.startswith("sk-ant-"):
        print("Ce n'est pas une clé Anthropic : elles commencent par « sk-ant- ».")
        return 1

    print("Essai auprès d'Anthropic…")
    acceptee, motif = essayer(cle)
    if not acceptee:
        print(f"Clé refusée ({motif}). Le fichier n'a pas été touché.")
        return 1

    ENV.write_text(remplacer(ENV.read_text(), cle))
    print("Clé acceptée et posée. Il reste à relancer le serveur : ./lancer-oris.command")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
