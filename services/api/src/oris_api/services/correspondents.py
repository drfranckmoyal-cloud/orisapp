"""Correspondants : le carnet d'adresses des confrères et des structures.

Personne ne se connecte à Oris avec ces fiches : elles servent à rattacher un patient
et à écrire le courrier d'adressage. Celui-ci est une **vraie lettre** — d'où l'adresse
postale, qui n'est pas un ornement.

Deux natures. Un praticien a une civilité, un prénom, une spécialité. Une structure
(CHU, service hospitalier) n'a rien de tout cela : lui coller un prénom vide et une
spécialité « non renseignée » serait prétendre qu'il lui en manque.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from oris_api.db.models import Correspondent, CorrespondentSpecialty, PatientCorrespondent
from oris_api.services import audit
from oris_api.services.errors import Conflict, NotFound, Unprocessable
from oris_api.services.identity import Actor

#: Connues d'avance, les mêmes pour tout le monde. Le cabinet ajoute les siennes depuis
#: les Paramètres ; on ne les écrit pas en base à la création d'une organisation, sinon
#: une liste par cabinet diverge dès le premier renommage.
SPECIALITES_STANDARD: tuple[str, ...] = ("Omnipraticien", "ODF", "CMF")

NATURES: frozenset[str] = frozenset({"practitioner", "organisation"})
#: La civilité n'a de sens que pour une personne, et sert à ouvrir la lettre.
CIVILITES: frozenset[str] = frozenset({"", "Dr", "Pr", "M.", "Mme"})


def specialites(session: Session, actor: Actor) -> list[str]:
    """Celles du code, puis celles du cabinet, sans doublon et rangées."""
    ajoutees = session.scalars(
        select(CorrespondentSpecialty.label).where(
            CorrespondentSpecialty.organization_id == actor.organization_id
        )
    )
    connues = set(SPECIALITES_STANDARD)
    return list(SPECIALITES_STANDARD) + sorted(label for label in ajoutees if label not in connues)


def ajouter_specialite(session: Session, actor: Actor, label: str) -> str:
    propre = " ".join(label.split())
    if not propre:
        raise Unprocessable("SPECIALTY_EMPTY")
    if propre.casefold() in {s.casefold() for s in specialites(session, actor)}:
        raise Conflict("SPECIALTY_EXISTS", propre)
    session.add(CorrespondentSpecialty(organization_id=actor.organization_id, label=propre))
    session.flush()
    audit.record(
        session, actor, "correspondent.specialty_added", "organization", actor.organization_id
    )
    return propre


def retirer_specialite(session: Session, actor: Actor, label: str) -> None:
    """Retirer une spécialité ajoutée. Celles du code ne se retirent pas.

    Les correspondants qui la portaient la gardent : ils rangent le libellé, pas un
    renvoi. Retirer la spécialité de la liste ne doit pas vider leur fiche.
    """
    if label in SPECIALITES_STANDARD:
        raise Unprocessable("SPECIALTY_BUILTIN", label)
    ligne = session.scalar(
        select(CorrespondentSpecialty).where(
            CorrespondentSpecialty.organization_id == actor.organization_id,
            CorrespondentSpecialty.label == label,
        )
    )
    if ligne is None:
        raise NotFound("SPECIALTY_NOT_FOUND", label)
    session.delete(ligne)
    audit.record(
        session, actor, "correspondent.specialty_removed", "organization", actor.organization_id
    )


def list_correspondents(
    session: Session, actor: Actor, query: str | None = None, specialty: str | None = None
) -> list[Correspondent]:
    statement = select(Correspondent).where(Correspondent.organization_id == actor.organization_id)
    if query:
        motif = f"%{query.strip()}%"
        statement = statement.where(
            or_(
                Correspondent.last_name.ilike(motif),
                Correspondent.first_name.ilike(motif),
                Correspondent.practice.ilike(motif),
            )
        )
    if specialty is not None:
        statement = statement.where(Correspondent.specialty == specialty)
        if specialty == "":
            # « Non renseignée » sert à retrouver les fiches **à compléter**. Une
            # structure n'a pas de spécialité par nature, pas par oubli : elle n'a rien
            # à faire dans cette liste.
            statement = statement.where(Correspondent.kind == "practitioner")
    # Les mis en avant d'abord : c'est à eux qu'on adresse le plus souvent.
    return list(
        session.scalars(
            statement.order_by(
                Correspondent.favorite.desc(),
                Correspondent.last_name,
                Correspondent.first_name,
            )
        )
    )


def get_correspondent(session: Session, actor: Actor, correspondent_id: UUID) -> Correspondent:
    correspondant = session.get(Correspondent, correspondent_id)
    if correspondant is None or correspondant.organization_id != actor.organization_id:
        raise NotFound("CORRESPONDENT_NOT_FOUND", str(correspondent_id))
    return correspondant


def _valider(nature: str, champs: dict[str, object]) -> dict[str, object]:
    """Une structure n'a ni civilité, ni prénom, ni spécialité : on les efface.

    Les accepter en silence laisserait dans la base un CHU nommé « Dr » avec un prénom,
    et la lettre ne saurait plus comment s'ouvrir.
    """
    if nature not in NATURES:
        raise Unprocessable("CORRESPONDENT_KIND_UNKNOWN", details=[nature])
    titre = str(champs.get("title", "") or "")
    if titre not in CIVILITES:
        raise Unprocessable("CORRESPONDENT_TITLE_UNKNOWN", details=[titre])
    if nature == "organisation":
        champs["title"] = ""
        champs["first_name"] = ""
        champs["specialty"] = ""
    return champs


def create_correspondent(session: Session, actor: Actor, **champs: object) -> Correspondent:
    nature = str(champs.get("kind") or "practitioner")
    champs = _valider(nature, {**champs, "kind": nature})
    correspondant = Correspondent(organization_id=actor.organization_id, **champs)
    session.add(correspondant)
    session.flush()
    audit.record(session, actor, "correspondent.created", "correspondent", correspondant.id)
    return correspondant


def update_correspondent(
    session: Session, actor: Actor, correspondent_id: UUID, changes: dict[str, object]
) -> Correspondent:
    correspondant = get_correspondent(session, actor, correspondent_id)
    nature = str(changes.get("kind") or correspondant.kind)
    fusion = {
        "title": correspondant.title,
        "first_name": correspondant.first_name,
        "specialty": correspondant.specialty,
        **changes,
    }
    fusion = _valider(nature, fusion)
    for champ in ("title", "first_name", "specialty"):
        changes[champ] = fusion[champ]
    changes["kind"] = nature
    for champ, valeur in changes.items():
        setattr(correspondant, champ, valeur)
    session.flush()
    audit.record(session, actor, "correspondent.updated", "correspondent", correspondant.id)
    return correspondant


def delete_correspondent(session: Session, actor: Actor, correspondent_id: UUID) -> None:
    correspondant = get_correspondent(session, actor, correspondent_id)
    session.delete(correspondant)
    audit.record(session, actor, "correspondent.deleted", "correspondent", correspondent_id)


# --- Rattachement à un patient ------------------------------------------------------
#
# Deux sens différents se cachent derrière le mot : **qui a adressé ce patient**, et
# **à qui on l'adresse**. Le rôle est donc porté par le lien, pas par le correspondant :
# le même confrère adresse un patient et en reçoit un autre.

ROLES: frozenset[str] = frozenset({"referred_by", "referred_to", "also_follows"})


def rattachements(
    session: Session, actor: Actor, patient_id: UUID
) -> list[tuple[PatientCorrespondent, Correspondent]]:
    """Les correspondants d'un patient, avec ce que chaque lien veut dire."""
    lignes = session.execute(
        select(PatientCorrespondent, Correspondent)
        .join(Correspondent, Correspondent.id == PatientCorrespondent.correspondent_id)
        .where(
            PatientCorrespondent.organization_id == actor.organization_id,
            PatientCorrespondent.patient_id == patient_id,
        )
        .order_by(Correspondent.last_name, Correspondent.first_name)
    )
    return [(lien, correspondant) for lien, correspondant in lignes]


def _lien(
    session: Session, actor: Actor, patient_id: UUID, correspondent_id: UUID
) -> PatientCorrespondent | None:
    return session.scalar(
        select(PatientCorrespondent).where(
            PatientCorrespondent.organization_id == actor.organization_id,
            PatientCorrespondent.patient_id == patient_id,
            PatientCorrespondent.correspondent_id == correspondent_id,
        )
    )


def rattacher(
    session: Session, actor: Actor, patient_id: UUID, correspondent_id: UUID, role: str
) -> PatientCorrespondent:
    """Rattacher, ou changer le rôle si le lien existe déjà.

    Refaire le geste avec un autre rôle corrige plutôt que de doubler la ligne : deux
    fois le même confrère sur une fiche, avec deux rôles, serait illisible.
    """
    if role not in ROLES:
        raise Unprocessable("CORRESPONDENT_ROLE_UNKNOWN", details=[role])
    # Lève si le correspondant n'est pas celui d'un autre cabinet.
    get_correspondent(session, actor, correspondent_id)

    existant = _lien(session, actor, patient_id, correspondent_id)
    if existant is not None:
        existant.role = role
        session.flush()
        audit.record(session, actor, "patient.correspondent_updated", "patient", patient_id)
        return existant

    lien = PatientCorrespondent(
        organization_id=actor.organization_id,
        patient_id=patient_id,
        correspondent_id=correspondent_id,
        role=role,
    )
    session.add(lien)
    session.flush()
    audit.record(session, actor, "patient.correspondent_attached", "patient", patient_id)
    return lien


def detacher(session: Session, actor: Actor, patient_id: UUID, correspondent_id: UUID) -> None:
    lien = _lien(session, actor, patient_id, correspondent_id)
    if lien is None:
        raise NotFound("CORRESPONDENT_LINK_NOT_FOUND", str(correspondent_id))
    session.delete(lien)
    audit.record(session, actor, "patient.correspondent_detached", "patient", patient_id)
