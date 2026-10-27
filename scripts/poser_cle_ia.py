"""Pose la clé Anthropic dans `services/api/.env`, après l'avoir essayée.

La clé est demandée sans être affichée, essayée contre l'API, et **n'est écrite que si
Anthropic l'accepte** : une clé fausse ne remplace jamais celle qui est en place. Elle
n'apparaît ni à l'écran, ni dans l'historique du terminal, ni dans un message.

    python3 scripts/poser_cle_ia.py
"""

from __future__ import annotations

import getpass
import json
import ssl
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


def main() -> int:
    if not ENV.exists():
        print(f"Pas de fichier {ENV} : rien à modifier.")
        return 1

    cle = getpass.getpass("Clé Anthropic (elle ne s'affiche pas) : ").strip()
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
