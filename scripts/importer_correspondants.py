"""Ajoute des correspondants au carnet d'adresses d'Oris, à partir d'une liste de noms.

Le classeur « Correspondants » de Franck ne contient que des noms, écrits comme Doctolib
les écrit : le nom de famille en capitales, puis le prénom (« VU VAN TUAN Yoann »). Ce
programme les coupe de la même façon que l'agenda, et **n'ajoute jamais deux fois le même
correspondant** : un nom déjà présent est laissé tel quel, avec sa fiche et ses adresses.

    python3 scripts/importer_correspondants.py --specialite ODF --fichier ortho.txt
    python3 scripts/importer_correspondants.py --specialite Omnipraticien \\
        --serveur https://51-159-130-158.nip.io/mobile --jeton "$JETON" --fichier omni.txt

Une ligne par correspondant. Les lignes vides et celles commençant par « # » sont
ignorées. Sans `--fichier`, la liste est lue sur l'entrée standard.
"""

from __future__ import annotations

import argparse
import json
import ssl
import sys
import unicodedata
import urllib.error
import urllib.request

CIVILITES = {"M", "Mme", "Mlle", "Mr", "Dr", "Pr"}


def separer_nom(ligne: str) -> tuple[str, str]:
    """« VU VAN TUAN Yoann » → (« Yoann », « VU VAN TUAN »).

    Même règle que l'agenda (`services/agenda.separer_nom`) : les mots en capitales font
    le nom, le reste fait le prénom. Tout en capitales ou tout en minuscules, on ne peut
    pas deviner : le premier mot fait le nom.
    """
    mots = [m for m in (ligne or "").replace("\xa0", " ").split() if m]
    while mots and mots[0].rstrip(".") in CIVILITES:
        mots.pop(0)
    nom = [m for m in mots if len(m) > 1 and m == m.upper()]
    prenom = [m for m in mots if m not in nom]
    if not nom or not prenom:
        nom, prenom = mots[:1], mots[1:]
    return " ".join(prenom), " ".join(nom)


def pareil(a: str, b: str) -> bool:
    """Deux écritures d'un même nom : accents, capitales et espaces n'y changent rien."""

    def nu(texte: str) -> str:
        sans_accent = unicodedata.normalize("NFKD", texte)
        return "".join(c for c in sans_accent if not unicodedata.combining(c)).upper().strip()

    return nu(a) == nu(b)


def _confiance() -> ssl.SSLContext | None:
    """Le magasin de certificats du Mac n'est pas celui de Python : sans `certifi`,
    l'adresse en https du serveur d'Oris est rejetée alors qu'elle est parfaitement
    valide. On ne désactive jamais la vérification, on lui donne de quoi vérifier."""
    try:
        import certifi
    except ImportError:
        return None
    return ssl.create_default_context(cafile=certifi.where())


def appeler(serveur: str, chemin: str, jeton: str, corps: dict | None = None) -> object:
    requete = urllib.request.Request(
        f"{serveur.rstrip('/')}{chemin}",
        data=json.dumps(corps).encode() if corps is not None else None,
        headers={
            "Content-Type": "application/json",
            **({"Authorization": f"Bearer {jeton}"} if jeton else {}),
        },
        method="POST" if corps is not None else "GET",
    )
    with urllib.request.urlopen(requete, timeout=30, context=_confiance()) as reponse:
        return json.loads(reponse.read() or "null")


def main() -> int:
    arguments = argparse.ArgumentParser(description=__doc__)
    arguments.add_argument("--serveur", default="http://localhost:8000")
    arguments.add_argument("--jeton", default="")
    arguments.add_argument("--specialite", required=True, help="ODF, Omnipraticien, CMF…")
    arguments.add_argument("--civilite", default="Dr")
    arguments.add_argument("--fichier", help="une ligne par correspondant ; défaut : stdin")
    arguments.add_argument("--pour-de-vrai", action="store_true", help="sinon, essai à blanc")
    options = arguments.parse_args()

    source = open(options.fichier, encoding="utf-8") if options.fichier else sys.stdin
    with source as lignes:
        noms = [l.strip() for l in lignes if l.strip() and not l.lstrip().startswith("#")]

    existants = appeler(options.serveur, "/correspondents", options.jeton)
    assert isinstance(existants, list)

    ajoutes, deja, sans_prenom = [], [], []
    for ligne in noms:
        prenom, nom = separer_nom(ligne)
        if not nom:
            continue
        connu = next(
            (
                c
                for c in existants
                if pareil(c.get("last_name", ""), nom)
                and (not prenom or not c.get("first_name") or pareil(c["first_name"], prenom))
            ),
            None,
        )
        if connu is not None:
            deja.append(f"{nom} {prenom}".strip())
            continue
        if not prenom:
            sans_prenom.append(nom)
        fiche = {
            "kind": "practitioner",
            "title": options.civilite,
            "last_name": nom,
            "first_name": prenom,
            "specialty": options.specialite,
        }
        if options.pour_de_vrai:
            appeler(options.serveur, "/correspondents", options.jeton, fiche)
        ajoutes.append(f"{nom} {prenom}".strip())

    verbe = "ajoutés" if options.pour_de_vrai else "à ajouter (essai à blanc)"
    print(f"{len(ajoutes)} {verbe} en « {options.specialite} » :")
    for nom in ajoutes:
        print("   ", nom)
    if deja:
        print(f"{len(deja)} déjà au carnet, laissés tels quels :")
        for nom in deja:
            print("   ", nom)
    if sans_prenom:
        print("Sans prénom — à compléter dans Oris :", ", ".join(sans_prenom))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
