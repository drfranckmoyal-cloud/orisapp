"""Préparer et faire l'envoi d'un document par courriel.

Destinataires proposés : le patient s'il a une adresse, et les correspondants rattachés
à sa fiche qui en ont une. Le correspondant principal est coché d'office — celui qui a
adressé le patient, ou, pour un courrier d'adressage, celui à qui on l'adresse.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from oris_api.config import Settings
from oris_api.db.models import DocumentRow, Encounter, Organization, Patient, User
from oris_api.documents.theme import Cabinet
from oris_api.services import audit, correspondents, deliveries, documents
from oris_api.services.attachments import Magasin
from oris_api.services.courriel import EnvoiImpossible, Messagerie, construire
from oris_api.services.errors import Conflict, NotFound, Unprocessable
from oris_api.services.identity import Actor

TITRES = {
    "consultation_note": "Compte rendu de consultation",
    "treatment_plan_text": "Plan de traitement",
    "operative_note": "Compte rendu opératoire",
    "referral_letter": "Courrier d'adressage",
    "patient_summary": "Résumé de consultation",
}


@dataclass(frozen=True)
class Candidat:
    cle: str  # « patient » ou l'identifiant du correspondant
    genre: str  # patient | correspondent
    libelle: str
    detail: str
    email: str
    coche: bool


@dataclass(frozen=True)
class Preparation:
    expediteur: str
    configure: bool
    raison: str | None
    candidats: list[Candidat]
    objet: str
    message: str
    brouillon: bool


def _contexte(
    session: Session, actor: Actor, document_id: UUID
) -> tuple[DocumentRow, Encounter, Patient, User | None]:
    document = session.get(DocumentRow, document_id)
    encounter = session.get(Encounter, document.encounter_id) if document else None
    if document is None or encounter is None or encounter.organization_id != actor.organization_id:
        raise NotFound("DOCUMENT_NOT_FOUND", str(document_id))
    if encounter.mode == "shadow":
        raise Conflict("SHADOW_ENCOUNTER", str(document_id))
    patient = session.get(Patient, encounter.patient_id)
    assert patient is not None  # noqa: S101 - clé étrangère non nulle
    return document, encounter, patient, session.get(User, actor.user_id)


def expediteur_de(user: User | None, settings: Settings) -> str:
    return (user.sending_email if user else "") or settings.smtp_user


def etat_boite(user: User | None, settings: Settings, configuree: bool) -> tuple[str, str | None]:
    """L'adresse d'envoi et, si l'envoi est impossible, pourquoi."""
    adresse = expediteur_de(user, settings)
    if not adresse:
        return "", "SENDING_EMAIL_MISSING"
    if not configuree:
        return adresse, "SMTP_NOT_CONFIGURED"
    return adresse, None


def _signature(session: Session, encounter: Encounter, user: User | None) -> str:
    organisation = session.get(Organization, encounter.organization_id)
    cabinet = Cabinet.from_identity(
        dict(organisation.identity or {}) if organisation else {},
        organisation.name if organisation else "",
    )
    nom = f"{cabinet.practitioner_title} {user.name if user else ''}".strip()
    lignes = [
        nom,
        *cabinet.qualification_lines()[:2],
        cabinet.name if cabinet.name != "Cabinet" else "",
    ]
    return "\n".join(line for line in lignes if line)


def preparer(
    session: Session, actor: Actor, document_id: UUID, settings: Settings, configuree: bool
) -> Preparation:
    document, encounter, patient, user = _contexte(session, actor, document_id)
    principal = "referred_to" if document.document_type == "referral_letter" else "referred_by"
    candidats: list[Candidat] = []
    if patient.email:
        candidats.append(
            Candidat(
                "patient",
                "patient",
                f"{patient.first_name} {patient.last_name}",
                "le patient",
                patient.email,
                False,
            )
        )
    for lien, fiche in correspondents.rattachements(session, actor, patient.id):
        adresse = fiche.email or fiche.secondary_email
        if not adresse:
            continue
        nom = " ".join(
            p.strip() for p in (fiche.title, fiche.first_name, fiche.last_name) if p.strip()
        )
        role = {
            "referred_by": "a adressé le patient",
            "referred_to": "patient adressé à",
            "also_follows": "suit aussi le patient",
        }.get(lien.role, "")
        candidats.append(
            Candidat(
                str(fiche.id),
                "correspondent",
                nom,
                " · ".join(p for p in (fiche.specialty, role) if p),
                adresse,
                lien.role == principal,
            )
        )
    adresse, raison = etat_boite(user, settings, configuree)
    moment = encounter.started_at or encounter.created_at
    titre = TITRES.get(document.document_type, "Document")
    qui = f"{patient.first_name} {patient.last_name.upper()}"
    objet = f"{titre} — {qui} — {moment.strftime('%d/%m/%Y')}"
    message = (
        "Cher confrère, chère consœur,\n\n"
        f"Veuillez trouver ci-joint le {titre[:1].lower() + titre[1:]} de {qui}, "
        f"établi à la suite de la consultation du {moment.strftime('%d/%m/%Y')}.\n\n"
        "Je reste à votre disposition pour tout complément.\n\n"
        "Bien confraternellement,\n\n"
        f"{_signature(session, encounter, user)}\n"
    )
    version = documents.current_version(session, document)
    brouillon = version is None or version.validated_at is None
    return Preparation(adresse, raison is None, raison, candidats, objet, message, brouillon)


@dataclass(frozen=True)
class Resultat:
    destinataire: str
    envoye: bool
    code: str | None


def envoyer(
    session: Session,
    actor: Actor,
    document_id: UUID,
    choix: list[str],
    adresses_libres: list[str],
    objet: str,
    message: str,
    settings: Settings,
    messagerie: Messagerie | None,
    magasin: Magasin | None,
) -> list[Resultat]:
    """Un message par destinataire, la pièce jointe en PDF ; chaque réussite est notée."""
    document, _, _, user = _contexte(session, actor, document_id)
    adresse, raison = etat_boite(user, settings, messagerie is not None)
    if raison or messagerie is None:
        raise Conflict(raison or "SMTP_NOT_CONFIGURED", str(document_id))
    if not choix and not adresses_libres:
        raise Unprocessable("NO_RECIPIENT", str(document_id))

    prepare = {c.cle: c for c in preparer(session, actor, document_id, settings, True).candidats}
    inconnus = [cle for cle in choix if cle not in prepare]
    if inconnus:
        raise Unprocessable("RECIPIENT_UNKNOWN", str(document_id), inconnus)
    for libre in adresses_libres:
        if "@" not in libre or " " in libre.strip():
            raise Unprocessable("EMAIL_INVALID", str(document_id), [libre])

    exporte = documents.export_document(session, actor, document_id, "pdf", magasin)
    resultats: list[Resultat] = []
    cibles = [(prepare[c], prepare[c].email) for c in choix] + [
        (None, a.strip()) for a in adresses_libres
    ]
    for candidat, email in cibles:
        courriel = construire(
            adresse,
            user.name if user else "",
            email,
            objet,
            message,
            exporte.payload,
            exporte.filename,
            document.id,
        )
        try:
            messagerie.envoyer(courriel)
        except EnvoiImpossible as echec:
            resultats.append(Resultat(email, False, echec.code))
            continue
        if candidat is None:
            deliveries.noter(session, actor, document.id, "other", "email", recipient_label=email)
        elif candidat.genre == "patient":
            deliveries.noter(session, actor, document.id, "patient", "email")
        else:
            deliveries.noter(
                session,
                actor,
                document.id,
                "correspondent",
                "email",
                correspondent_id=UUID(candidat.cle),
            )
        resultats.append(Resultat(email, True, None))
    audit.record(
        session,
        actor,
        "document.emailed",
        "document",
        document.id,
        sent=sum(r.envoye for r in resultats),
        failed=sum(not r.envoye for r in resultats),
    )
    return resultats
