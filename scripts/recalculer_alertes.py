"""Repasse le contrôle factuel sur les documents déjà écrits.

Les alertes d'un document sont figées au moment où il est validé. Quand une règle
change — parce qu'elle se trompait, ou parce qu'elle disait vingt-six fois ce qui se dit
une fois — les documents d'hier gardent les alertes d'hier. Ce programme les relit avec
les règles d'aujourd'hui. **Rien n'est réécrit** : le texte ne bouge pas, le dossier
clinique non plus, seules les alertes sont recalculées.

    python3 scripts/recalculer_alertes.py                 # essai à blanc
    python3 scripts/recalculer_alertes.py --pour-de-vrai

À lancer depuis `services/api` (le fichier `.env` y est lu), ou avec `DATABASE_URL` posé.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent / "services" / "api"
sys.path.insert(0, str(RACINE / "src"))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from oris_api.config import Settings  # noqa: E402
from oris_api.db.models import DocumentRow, DocumentVersion, Encounter  # noqa: E402
from oris_api.db.session import get_engine  # noqa: E402
from oris_api.services.clinical_store import load_current  # noqa: E402
from oris_api.services.documents import relire  # noqa: E402


def main() -> int:
    arguments = argparse.ArgumentParser(description=__doc__)
    arguments.add_argument("--pour-de-vrai", action="store_true", help="sinon, essai à blanc")
    options = arguments.parse_args()

    with Session(get_engine()) as session:
        documents = session.scalars(select(DocumentRow)).all()
        change = 0
        for document in documents:
            version = session.get(DocumentVersion, document.current_version_id)
            encounter = session.get(Encounter, document.encounter_id)
            if version is None or encounter is None:
                continue
            objet = load_current(session, encounter)
            avant = list(version.validation_issues or [])
            apres = [issue.__dict__ for issue in relire(document, version, objet)]
            if len(avant) == len(apres) and {i["code"] for i in avant} == {
                i["code"] for i in apres
            }:
                continue
            change += 1
            print(
                f"  {document.document_type} ({str(document.id)[:8]}) : "
                f"{len(avant)} alerte(s) → {len(apres)}"
            )
            for code in sorted({i["code"] for i in avant} - {i["code"] for i in apres}):
                print(f"      disparue : {code}")
            for code in sorted({i["code"] for i in apres} - {i["code"] for i in avant}):
                print(f"      nouvelle : {code}")
            if options.pour_de_vrai:
                version.validation_issues = apres
        if options.pour_de_vrai:
            session.commit()
    verbe = "recalculé(s)" if options.pour_de_vrai else "à recalculer (essai à blanc)"
    print(f"{change} document(s) {verbe} sur {len(documents)}.")
    print(f"base : {Settings().database_url.split('@')[-1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
