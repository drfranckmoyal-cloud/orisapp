#!/usr/bin/env python3
"""Brancher l'envoi des documents sur Gmail, par le web — un clic « Autoriser » du praticien.

Pourquoi : l'hébergeur du serveur en ligne (Scaleway) bloque les ports de courriel tant
que le compte n'a pas fait sa vérification d'identité. L'API de Gmail passe par le web
ordinaire, qu'il ne bloque pas (Franck, 12/11/2026 : « envoyer avec mon adresse mail »).

Ce que fait ce script, sur le Mac :
1. ouvre dans le navigateur la page Google qui demande au praticien d'autoriser Oris à
   **envoyer** des courriels depuis sa boîte — et rien d'autre (ni lecture, ni suppression) ;
2. reçoit la réponse de Google sur le Mac lui-même (127.0.0.1), vérifie le compte ;
3. range l'accès dans le `.env` du serveur en ligne (par SSH, jamais à l'écran), puis
   redémarre le serveur clinique.

L'identifiant du « client » Google est celui du projet Google Cloud que Franck a créé pour
son assistant personnel ; on le passe par `--client` (un fichier JSON téléchargé de la
console Google). Rien n'est écrit dans le dépôt.

    python3 scripts/autoriser_gmail.py --client <google-client.json> --compte <adresse>

Pour retirer l'accès : https://myaccount.google.com/permissions
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import http.server
import json
import secrets
import shlex
import ssl
import subprocess
import sys
import threading
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

try:
    import certifi

    CONTEXTE = ssl.create_default_context(cafile=certifi.where())
except ImportError:  # le Python du Mac sans certifi : le magasin système
    CONTEXTE = ssl.create_default_context()

PORTEES = "https://www.googleapis.com/auth/gmail.send https://www.googleapis.com/auth/userinfo.email"
AUTORISATION = "https://accounts.google.com/o/oauth2/v2/auth"
JETON = "https://oauth2.googleapis.com/token"
IDENTITE = "https://www.googleapis.com/oauth2/v3/userinfo"
SERVEUR = "root@51.159.130.158"
ENV_SERVEUR = "/home/oris/app/services/api/.env"


def _post(adresse: str, champs: dict[str, str]) -> dict:
    requete = urllib.request.Request(
        adresse,
        data=urllib.parse.urlencode(champs).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(requete, timeout=30, context=CONTEXTE) as reponse:
        return json.loads(reponse.read())


def consentement(client_id: str, client_secret: str, compte: str) -> dict:
    """Ouvre la page Google et attend la réponse sur le Mac."""
    verificateur = secrets.token_urlsafe(64)
    defi = base64.urlsafe_b64encode(hashlib.sha256(verificateur.encode()).digest()).rstrip(b"=")
    etat = secrets.token_urlsafe(16)
    recu: dict[str, str] = {}

    class Retour(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 - nom imposé
            parametres = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(self.path).query))
            if "code" not in parametres and "error" not in parametres:
                self.send_response(404)
                self.end_headers()
                return
            recu.update(parametres)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            texte = (
                "C'est fait : Oris peut envoyer vos documents. Vous pouvez fermer cet onglet."
                if "code" in parametres
                else "Autorisation refusée : rien n'a changé. Vous pouvez fermer cet onglet."
            )
            self.wfile.write(f"<p style='font:18px sans-serif;margin:3em'>{texte}</p>".encode())

        def log_message(self, *args: object) -> None:
            pass

    serveur = http.server.HTTPServer(("127.0.0.1", 0), Retour)
    retour = f"http://127.0.0.1:{serveur.server_port}"
    fil = threading.Thread(target=serveur.handle_request, daemon=True)
    fil.start()
    adresse = AUTORISATION + "?" + urllib.parse.urlencode(
        {
            "client_id": client_id,
            "redirect_uri": retour,
            "response_type": "code",
            "scope": PORTEES,
            "access_type": "offline",
            "prompt": "consent",
            "login_hint": compte,
            "state": etat,
            "code_challenge": defi.decode(),
            "code_challenge_method": "S256",
        }
    )
    print("Une page Google s'ouvre : choisissez", compte, "puis « Autoriser ».")
    webbrowser.open(adresse)
    fil.join(timeout=600)
    serveur.server_close()
    if recu.get("state") != etat or "code" not in recu:
        sys.exit(f"Pas d'autorisation reçue ({recu.get('error', 'délai dépassé')}) : rien n'a changé.")
    return _post(
        JETON,
        {
            "client_id": client_id,
            "client_secret": client_secret,
            "code": recu["code"],
            "code_verifier": verificateur,
            "grant_type": "authorization_code",
            "redirect_uri": retour,
        },
    )


def adresse_du_compte(jeton_du_moment: str) -> str:
    requete = urllib.request.Request(IDENTITE, headers={"Authorization": f"Bearer {jeton_du_moment}"})
    with urllib.request.urlopen(requete, timeout=30, context=CONTEXTE) as reponse:
        return str(json.loads(reponse.read()).get("email", ""))


# Exécuté sur le serveur : remplace (ou ajoute) les trois lignes GMAIL_ du .env, lues sur
# l'entrée standard — jamais sur la ligne de commande, qui se voit dans la liste des process.
POSER = r"""
import json, sys, os
valeurs = json.load(sys.stdin)
chemin = sys.argv[1]
lignes = open(chemin).read().splitlines()
lignes = [l for l in lignes if not any(l.startswith(c + "=") for c in valeurs)]
lignes += [f"{c}={v}" for c, v in valeurs.items()]
temporaire = chemin + ".nouveau"
with open(temporaire, "w") as f:
    f.write("\n".join(lignes) + "\n")
os.chmod(temporaire, 0o600)
os.rename(temporaire, chemin)
"""


def poser_sur_le_serveur(valeurs: dict[str, str]) -> None:
    commande = (
        f"python3 -c {shlex.quote(POSER)} {ENV_SERVEUR} && chown oris:oris {ENV_SERVEUR}"
        " && systemctl restart oris-api"
    )
    subprocess.run(
        ["ssh", "-o", "ConnectTimeout=15", SERVEUR, commande],
        input=json.dumps(valeurs).encode(),
        check=True,
    )


def main() -> None:
    lecteur = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    lecteur.add_argument("--client", type=Path, required=True)
    lecteur.add_argument("--compte", required=True)
    arguments = lecteur.parse_args()
    client = json.loads(arguments.client.read_text())
    client = client.get("installed") or client.get("web") or client
    reponse = consentement(client["client_id"], client["client_secret"], arguments.compte)
    durable = reponse.get("refresh_token")
    if not durable:
        sys.exit("Google n'a pas donné d'accès durable : rien n'a changé.")
    if "gmail.send" not in reponse.get("scope", ""):
        sys.exit("L'envoi de courriels n'a pas été autorisé (case décochée ?) : rien n'a changé.")
    compte = adresse_du_compte(reponse["access_token"])
    if compte.lower() != arguments.compte.lower():
        sys.exit(f"Autorisé depuis {compte}, pas {arguments.compte} : rien n'a changé. Relancez.")
    poser_sur_le_serveur(
        {
            "GMAIL_CLIENT_ID": client["client_id"],
            "GMAIL_CLIENT_SECRET": client["client_secret"],
            "GMAIL_REFRESH_TOKEN": durable,
        }
    )
    print(f"C'est branché : Oris envoie désormais depuis {compte}, par le web.")


if __name__ == "__main__":
    main()
