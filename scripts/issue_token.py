#!/usr/bin/env python3
"""Crée un jeton d'accès Oris pour un praticien. Le secret n'est affiché qu'une fois.

    services/api/.venv/bin/python scripts/issue_token.py --email praticien@cabinet.fr \
        --label "iPhone du cabinet"
    services/api/.venv/bin/python scripts/issue_token.py --list
    services/api/.venv/bin/python scripts/issue_token.py --revoke <id>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "services/api/src"))

from sqlalchemy import create_engine, select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from oris_api.config import get_settings  # noqa: E402
from oris_api.db.models import ApiToken, User  # noqa: E402
from oris_api.services import authentication  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", help="praticien à qui appartient le jeton")
    parser.add_argument("--label", default="jeton", help="à quoi sert ce jeton")
    parser.add_argument("--list", action="store_true", help="lister les jetons existants")
    parser.add_argument("--revoke", help="révoquer un jeton par son identifiant")
    args = parser.parse_args()

    engine = create_engine(get_settings().database_url)
    with Session(engine) as session:
        if args.list:
            for token in session.scalars(select(ApiToken).order_by(ApiToken.created_at)):
                state = "révoqué" if token.revoked_at else "actif"
                used = token.last_used_at.strftime("%d/%m/%Y") if token.last_used_at else "jamais"
                print(f"{token.id}  {state:8}  {token.label:30}  dernier usage : {used}")
            return 0

        if args.revoke:
            authentication.revoke(session, UUID(args.revoke))
            session.commit()
            print("Jeton révoqué : il ne donne plus accès à rien.")
            return 0

        if not args.email:
            parser.error("--email est requis pour créer un jeton")
        user = session.scalar(select(User).where(User.email == args.email))
        if user is None:
            print(f"Aucun praticien avec l'adresse {args.email}", file=sys.stderr)
            return 1
        issued = authentication.issue(session, user.id, args.label)
        session.commit()
        print("Jeton créé. Notez-le maintenant : il ne sera plus jamais affiché.\n")
        print(f"  identifiant : {issued.token_id}")
        print(f"  intitulé    : {issued.label}")
        print(f"  secret      : {issued.secret}\n")
        print("À envoyer dans chaque requête : Authorization: Bearer <secret>")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
