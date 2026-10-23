"""Pose (ou remplace) le mot de passe d'un praticien, et corrige son adresse au besoin.

Il n'y a pas encore d'écran pour ça : la création de cabinet et l'invitation d'un
confrère sont la suite de l'étape 1. En attendant, c'est par ici — sur le Mac, ou sur le
serveur en ligne par `ssh`.

    python3 scripts/poser_mot_de_passe.py --email vous@exemple.fr
    python3 scripts/poser_mot_de_passe.py --email ancienne@adresse --nouvelle-adresse vous@exemple.fr

Le mot de passe est demandé sans être affiché, et n'est jamais écrit : la base n'en garde
qu'une empreinte scrypt.
"""

from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent / "services" / "api"
sys.path.insert(0, str(RACINE / "src"))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from oris_api.db.models import User  # noqa: E402
from oris_api.db.session import get_engine  # noqa: E402
from oris_api.services import authentication  # noqa: E402


def main() -> int:
    arguments = argparse.ArgumentParser(description=__doc__)
    arguments.add_argument("--email", required=True, help="l'adresse du compte à modifier")
    arguments.add_argument("--nouvelle-adresse", help="pour remplacer l'adresse du compte")
    options = arguments.parse_args()

    with Session(get_engine()) as session:
        user = session.scalar(select(User).where(User.email == options.email.strip().lower()))
        if user is None:
            print(f"Aucun compte avec l'adresse « {options.email} ».")
            for connu in session.scalars(select(User).order_by(User.name)):
                print("   comptes existants :", connu.name, "·", connu.email)
            return 1

        mot_de_passe = getpass.getpass(f"Mot de passe pour {user.name} : ")
        if mot_de_passe != getpass.getpass("Confirmez : "):
            print("Les deux saisies diffèrent : rien n'a été changé.")
            return 1

        try:
            authentication.poser_mot_de_passe(session, user, mot_de_passe)
        except Exception as refus:  # noqa: BLE001 - le motif se lit tel quel
            print("Refusé :", refus)
            return 1

        if options.nouvelle_adresse:
            user.email = options.nouvelle_adresse.strip().lower()
        session.commit()
        print(f"Mot de passe posé pour {user.name}. Identifiant : {user.email}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
