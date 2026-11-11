"""Le relevé des corrections de la semaine, pour en tirer des règles.

Franck, le 11/11/2026 : « les corrections qu'on fait, elles servent comme adaptation de
nouvelles règles ? » — puis : « oui, mets-le en place ». Chaque semaine, ce relevé réunit
ce que le praticien a corrigé, pour repérer ce qui revient et proposer de changer la
règle à la source (comme l'ordonnance de kiné rangée dans le motif).

Oris ne change jamais ses règles tout seul : le relevé **propose**, le praticien décide,
et la règle se change exprès, testée (CLAUDE.md, invariants d'apprentissage).

Tourne sur le serveur en ligne ; écrit du Markdown sur la sortie standard. Aucun nom de
patient : les consultations sont désignées par la date et une initiale.

    ssh root@… "su - oris -c 'cd /home/oris/app/services/api && .venv/bin/python ../../scripts/releve_corrections.py --jours 7'"
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent / "services" / "api"
sys.path.insert(0, str(RACINE / "src"))

from oris_api.db.models import (
    DemandeCorrectionRow,
    DocumentRow,
    DocumentVersion,
    Encounter,
    LearningEventRow,
    Patient,
)
from oris_api.db.session import get_engine
from sqlalchemy import select
from sqlalchemy.orm import Session

LIBELLES = {
    "tooth_number_correction": "numéro de dent corrigé",
    "clinical_fact_added": "fait ajouté",
    "clinical_fact_removed": "fait retiré",
    "clinical_fact_corrected": "fait corrigé",
    "negation_correction": "négation corrigée",
    "temporality_correction": "temporalité corrigée",
    "certainty_correction": "certitude corrigée",
    "treatment_status_correction": "statut d'un traitement corrigé",
    "speaker_role_correction": "qui parle, corrigé",
    "transcript_word_correction": "mot de la transcription corrigé",
    "document_text_edit": "texte réécrit à la main",
    "style_preference_detected": "consigne de rédaction",
}


def designer(session: Session, encounter_id: object) -> str:
    rencontre = session.get(Encounter, encounter_id)
    if rencontre is None:
        return "consultation retirée"
    patient = session.get(Patient, rencontre.patient_id)
    initiale = (
        (patient.last_name[:1].upper() + ".") if patient and patient.last_name else "?"
    )
    quand = rencontre.started_at or rencontre.created_at
    return f"{initiale} du {quand:%d/%m}"


def phrases(texte: str) -> list[str]:
    morceaux = re.split(r"(?<=[.!?])\s+|\n+", texte or "")
    return [" ".join(m.split()) for m in morceaux if len(m.split()) >= 3]


def ecart(session: Session, encounter_id: object, document_type: str) -> str:
    """Ce que le praticien a changé à la main dans le texte rédigé par Oris : c'est là que
    se lisent les règles à corriger (une phrase déplacée, une formule retirée…)."""
    document = session.scalar(
        select(DocumentRow).where(
            DocumentRow.encounter_id == encounter_id,
            DocumentRow.document_type == document_type,
        )
    )
    if document is None:
        return "Document retiré."
    versions = list(
        session.scalars(
            select(DocumentVersion)
            .where(DocumentVersion.document_id == document.id)
            .order_by(DocumentVersion.version)
        )
    )
    main = next(
        (v for v in reversed(versions) if v.generator == "practitioner:manual"), None
    )
    if main is None:
        return "Pas de texte écrit à la main."
    oris = next(
        (
            v
            for v in reversed(versions)
            if v.version < main.version and v.generator != "practitioner:manual"
        ),
        None,
    )
    if oris is None:
        return "Pas de version d'Oris à comparer."
    avant, apres = phrases(oris.content), phrases(main.content)
    retirees = [s for s in avant if s not in apres]
    ajoutees = [s for s in apres if s not in avant]
    lignes = []
    for s in retirees[:8]:
        lignes.append(f"- retiré ou changé : « {s} »")
    for s in ajoutees[:8]:
        lignes.append(f"- écrit par le praticien : « {s} »")
    return "\n".join(lignes) or "Mise en forme seulement (aucune phrase changée)."


def main() -> int:
    options = argparse.ArgumentParser(description=__doc__)
    options.add_argument("--jours", type=int, default=7)
    jours = options.parse_args().jours
    depuis = datetime.now(UTC) - timedelta(days=jours)

    with Session(get_engine()) as session:
        evenements = list(
            session.scalars(
                select(LearningEventRow)
                .where(LearningEventRow.created_at >= depuis)
                .order_by(LearningEventRow.created_at)
            )
        )
        demandes = list(
            session.scalars(
                select(DemandeCorrectionRow)
                .where(DemandeCorrectionRow.created_at >= depuis)
                .order_by(DemandeCorrectionRow.created_at)
            )
        )
        replis = session.execute(
            select(DocumentVersion.generator, DocumentRow.encounter_id)
            .join(DocumentRow, DocumentRow.id == DocumentVersion.document_id)
            .where(DocumentVersion.created_at >= depuis)
        ).all()

        print(f"# Relevé des corrections — {jours} derniers jours")
        print(f"\n_Établi le {datetime.now(UTC):%d/%m/%Y à %H:%M} UTC._\n")

        compte = Counter(e.event_type for e in evenements)
        print("## Corrections du dossier et du texte\n")
        if not compte:
            print("Aucune.\n")
        for type_, n in compte.most_common():
            print(f"- {LIBELLES.get(type_, type_)} : {n}")

        print("\n## Demandes à « Corriger avec Claude »\n")
        if not demandes:
            print("Aucune.\n")
        for d in demandes:
            lecture = (d.reponse or {}).get("lecture") or {}
            nature = lecture.get("nature", "")
            consigne = lecture.get("consigne", "")
            ligne = f"- [{designer(session, d.encounter_id)}] « {d.texte} » — {d.etat}"
            if nature:
                ligne += f" · {nature}"
            if consigne:
                ligne += f" · consigne : {consigne}"
            if d.etat == "echec" and (d.reponse or {}).get("code"):
                ligne += f" · panne : {d.reponse['code']}"
            print(ligne)

        print("\n## Consignes de rédaction données\n")
        consignes = [
            (e.after or {}).get("preference", "")
            for e in evenements
            if e.event_type == "style_preference_detected"
        ]
        if not consignes:
            print("Aucune.\n")
        for consigne, n in Counter(c for c in consignes if c).most_common():
            print(f"- {consigne} ({n} fois)")

        print("\n## Textes réécrits à la main\n")
        reecrits = [e for e in evenements if e.event_type == "document_text_edit"]
        if not reecrits:
            print("Aucun.\n")
        vus: set[object] = set()
        for e in reecrits:
            doc = (e.after or {}).get("document_type", "")
            if (e.encounter_id, doc) in vus:
                continue
            vus.add((e.encounter_id, doc))
            print(f"\n### [{designer(session, e.encounter_id)}] {doc}\n")
            print(ecart(session, e.encounter_id, doc))

        print("\n## Rédactions retombées en version de secours\n")
        secours = [enc for gen, enc in replis if "(repli)" in (gen or "")]
        if not secours:
            print("Aucune.\n")
        for enc in sorted(set(secours), key=str):
            print(f"- {designer(session, enc)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
