"""Pièces jointes du patient : photos, radios, empreintes, documents (spec §55).

Trois règles tiennent ce fichier :

- **Oris ne lit pas les pièces jointes.** Elles accompagnent le compte rendu, elles
  ne le nourrissent jamais : aucun fait clinique n'en sort. Le praticien les cite
  s'il le veut, en écrivant.
- **Le fichier n'entre pas en base.** La base garde son nom, sa taille, son
  empreinte et l'endroit où il est rangé. Le contenu vit dans le magasin de
  fichiers, comme l'audio.
- **Rien n'est accepté sans être reconnu.** Un format inconnu est refusé, pas rangé
  « au cas où » : un fichier qu'on ne sait pas rouvrir n'a pas sa place au dossier.
"""

from __future__ import annotations

import hashlib
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from oris_api.config import Settings
from oris_api.db.models import Attachment, Patient
from oris_api.services import audit
from oris_api.services.errors import NotFound, Unprocessable
from oris_api.services.identity import Actor

# Ce qu'un cabinet dentaire produit réellement. L'extension fait foi : un client qui
# annonce mal son type ne doit pas pouvoir faire entrer n'importe quoi.
FORMATS: dict[str, tuple[str, str]] = {
    # extension : (type de média, nature)
    ".jpg": ("image/jpeg", "photo"),
    ".jpeg": ("image/jpeg", "photo"),
    ".png": ("image/png", "photo"),
    ".heic": ("image/heic", "photo"),
    ".heif": ("image/heif", "photo"),
    ".webp": ("image/webp", "photo"),
    ".tif": ("image/tiff", "radio"),
    ".tiff": ("image/tiff", "radio"),
    ".dcm": ("application/dicom", "radio"),
    ".stl": ("model/stl", "empreinte"),
    ".ply": ("model/mesh", "empreinte"),
    ".obj": ("model/obj", "empreinte"),
    ".pdf": ("application/pdf", "document"),
}

MAX_BYTES = 80 * 1024 * 1024  # 80 Mo : un STL de maxillaire complet y tient
NOM_PROPRE = re.compile(r"[^A-Za-z0-9._-]+")


@dataclass(frozen=True)
class Magasin:
    """Où vivent les fichiers. Un dossier par patient, un fichier par pièce."""

    racine: Path

    def chemin(self, patient_id: UUID, cle: str) -> Path:
        return self.racine / str(patient_id) / cle

    def ranger(self, patient_id: UUID, cle: str, contenu: bytes) -> None:
        cible = self.chemin(patient_id, cle)
        cible.parent.mkdir(parents=True, exist_ok=True)
        cible.write_bytes(contenu)

    def lire(self, patient_id: UUID, cle: str) -> bytes | None:
        cible = self.chemin(patient_id, cle)
        return cible.read_bytes() if cible.exists() else None

    def retirer(self, patient_id: UUID, cle: str) -> None:
        self.chemin(patient_id, cle).unlink(missing_ok=True)

    def vider(self, patient_id: UUID) -> None:
        shutil.rmtree(self.racine / str(patient_id), ignore_errors=True)


def magasin_de(settings: Settings) -> Magasin:
    return Magasin(racine=settings.attachment_dir)


def nom_sur(nom: str) -> str:
    """Un nom de fichier qui ne peut pas sortir de son dossier."""
    propre = NOM_PROPRE.sub("-", Path(nom).name).strip("-.")
    return propre[:200] or "fichier"


def reconnaitre(nom: str) -> tuple[str, str]:
    """Rend (type de média, nature) ou refuse."""
    extension = Path(nom).suffix.lower()
    reconnu = FORMATS.get(extension)
    if reconnu is None:
        raise Unprocessable("UNSUPPORTED_ATTACHMENT_FORMAT", nom, sorted(FORMATS))
    return reconnu


def list_attachments(session: Session, patient: Patient) -> list[Attachment]:
    return list(
        session.scalars(
            select(Attachment)
            .where(Attachment.patient_id == patient.id)
            .order_by(Attachment.created_at.desc())
        )
    )


def get_attachment(session: Session, actor: Actor, attachment_id: UUID) -> Attachment:
    piece = session.get(Attachment, attachment_id)
    if piece is None:
        raise NotFound("ATTACHMENT_NOT_FOUND", str(attachment_id))
    patient = session.get(Patient, piece.patient_id)
    if patient is None or patient.organization_id != actor.organization_id:
        raise NotFound("ATTACHMENT_NOT_FOUND", str(attachment_id))
    return piece


def add_attachment(
    session: Session,
    actor: Actor,
    magasin: Magasin,
    patient: Patient,
    filename: str,
    contenu: bytes,
    encounter_id: UUID | None = None,
    label: str = "",
) -> Attachment:
    if not contenu:
        raise Unprocessable("EMPTY_ATTACHMENT", filename)
    if len(contenu) > MAX_BYTES:
        raise Unprocessable("ATTACHMENT_TOO_LARGE", filename, [str(MAX_BYTES)])

    nom = nom_sur(filename)
    media_type, nature = reconnaitre(nom)
    empreinte = hashlib.sha256(contenu).hexdigest()

    # Le même fichier importé deux fois ne se range qu'une : l'empreinte le dit.
    deja = session.execute(
        select(Attachment).where(
            Attachment.patient_id == patient.id, Attachment.checksum == empreinte
        )
    ).scalar_one_or_none()
    if deja is not None:
        return deja

    cle = f"{uuid4().hex}{Path(nom).suffix.lower()}"
    magasin.ranger(patient.id, cle, contenu)
    piece = Attachment(
        patient_id=patient.id,
        encounter_id=encounter_id,
        kind=nature,
        filename=nom,
        media_type=media_type,
        byte_size=len(contenu),
        checksum=empreinte,
        storage_key=cle,
        label=label.strip(),
    )
    session.add(piece)
    session.flush()
    # Le journal retient qu'une pièce est entrée, jamais ce qu'elle montre.
    audit.record(session, actor, "attachment.added", "patient", patient.id)
    return piece


def remove_attachment(
    session: Session, actor: Actor, magasin: Magasin, attachment_id: UUID
) -> None:
    piece = get_attachment(session, actor, attachment_id)
    magasin.retirer(piece.patient_id, piece.storage_key)
    session.delete(piece)
    session.flush()
    audit.record(session, actor, "attachment.removed", "patient", piece.patient_id)


def read_attachment(magasin: Magasin, piece: Attachment) -> bytes:
    contenu = magasin.lire(piece.patient_id, piece.storage_key)
    if contenu is None:
        # Le fichier a disparu du magasin : on le dit, on n'invente pas un vide.
        raise NotFound("ATTACHMENT_FILE_MISSING", str(piece.id))
    return contenu
