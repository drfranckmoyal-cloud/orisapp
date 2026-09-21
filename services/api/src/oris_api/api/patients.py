"""Routes patients (spec §58)."""

from __future__ import annotations

import hashlib
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, File, Form, Header, Response, UploadFile, status

from oris_api.api.dependencies import ActorDep, MagasinDep, ProvidersDep, SessionDep
from oris_api.api.schemas import (
    AttachmentOut,
    CorrespondentOut,
    DictationOut,
    PatientCreate,
    PatientListOut,
    PatientOut,
    PatientUpdate,
    RattachementIn,
    RattachementOut,
)
from oris_api.db.models import Attachment
from oris_api.domain.types import AudioChunk
from oris_api.providers.base import TranscriptionUnavailable
from oris_api.services import (
    async_bridge,
    attachments,
    audio,
    correspondents,
    encounters,
    patients,
)
from oris_api.services.errors import Conflict, Unprocessable

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("", response_model=list[PatientListOut])
def list_patients(
    session: SessionDep, actor: ActorDep, q: str | None = None
) -> list[PatientListOut]:
    resumes = patients.resumes(session, actor)
    vide = patients.Resume()
    liste = []
    for patient in patients.list_patients(session, actor, q):
        resume = resumes.get(patient.id, vide)
        liste.append(
            PatientListOut(
                **PatientOut.model_validate(patient).model_dump(),
                consultations=resume.consultations,
                derniere_consultation=resume.derniere,
                a_relire=resume.a_relire,
            )
        )
    return liste


@router.post("", response_model=PatientOut, status_code=status.HTTP_201_CREATED)
def create_patient(body: PatientCreate, session: SessionDep, actor: ActorDep) -> PatientOut:
    patient = patients.create_patient(session, actor, **body.model_dump())
    return PatientOut.model_validate(patient)


@router.get("/{patient_id}", response_model=PatientOut)
def get_patient(patient_id: UUID, session: SessionDep, actor: ActorDep) -> PatientOut:
    return PatientOut.model_validate(patients.get_patient(session, actor, patient_id))


@router.patch("/{patient_id}", response_model=PatientOut)
def update_patient(
    patient_id: UUID, body: PatientUpdate, session: SessionDep, actor: ActorDep
) -> PatientOut:
    changes = body.model_dump(exclude_unset=True)
    return PatientOut.model_validate(patients.update_patient(session, actor, patient_id, changes))


@router.post("/{patient_id}/note/dictation", response_model=DictationOut)
def dictate_note(
    patient_id: UUID,
    payload: Annotated[bytes, Body(media_type=audio.AUDIO_FORMAT)],
    content_type: Annotated[str, Header()],
    session: SessionDep,
    actor: ActorDep,
    providers: ProvidersDep,
) -> DictationOut:
    """Dicter la note administrative : le son est transcrit, puis oublié.

    Il n'est **jamais stocké** — ni en base, ni sur disque : transcrit dans la requête
    et rendu au praticien, qui relit avant d'enregistrer. La note reste administrative :
    rien de ce qui est dicté ici n'entre dans un dossier clinique.
    """
    patient = patients.get_patient(session, actor, patient_id)
    if content_type.replace(" ", "").lower() != audio.AUDIO_FORMAT:
        raise Unprocessable("UNSUPPORTED_AUDIO_FORMAT", str(patient.id))
    if not payload or len(payload) % 2:
        raise Unprocessable("INVALID_CHUNK", str(patient.id))

    chunk = AudioChunk(
        session_id=str(patient.id),
        sequence=0,
        timestamp_ms=0,
        checksum=hashlib.sha256(payload).hexdigest(),
        payload=payload,
    )
    try:
        transcription = async_bridge.run(
            lambda: providers.speech_to_text.transcribe([chunk], encounters.LOCALE, [])
        )
    except TranscriptionUnavailable as error:
        raise Conflict("STT_UNAVAILABLE", str(patient.id), [error.code]) from error

    texte = " ".join(segment.text for segment in transcription.segments).strip()
    return DictationOut(text=texte)


# --- Pièces jointes (spec §55) ---------------------------------------------------------


def piece_out(piece: Attachment) -> AttachmentOut:
    return AttachmentOut(
        id=piece.id,
        filename=piece.filename,
        media_type=piece.media_type,
        kind=piece.kind,
        byte_size=piece.byte_size,
        label=piece.label,
        encounter_id=piece.encounter_id,
        created_at=piece.created_at,
    )


@router.get("/{patient_id}/attachments", response_model=list[AttachmentOut])
def list_attachments(patient_id: UUID, session: SessionDep, actor: ActorDep) -> list[AttachmentOut]:
    patient = patients.get_patient(session, actor, patient_id)
    return [piece_out(p) for p in attachments.list_attachments(session, patient)]


@router.post(
    "/{patient_id}/attachments",
    response_model=list[AttachmentOut],
    status_code=status.HTTP_201_CREATED,
)
async def add_attachments(
    patient_id: UUID,
    session: SessionDep,
    actor: ActorDep,
    magasin: MagasinDep,
    fichiers: Annotated[list[UploadFile], File(alias="files")],
    encounter_id: Annotated[UUID | None, Form()] = None,
) -> list[AttachmentOut]:
    """Importer des photos, radios, empreintes ou documents.

    Oris ne les lit pas : elles accompagnent le compte rendu, elles ne le nourrissent
    jamais. Un format inconnu est refusé plutôt que rangé « au cas où ».

    `encounter_id` rattache la pièce à une consultation — c'est le cas quand on
    l'importe depuis l'écran de révision. Elle reste celle du patient : on la
    retrouvera depuis sa fiche.
    """
    patient = patients.get_patient(session, actor, patient_id)
    if encounter_id is not None:
        # La consultation doit exister et appartenir au même praticien.
        encounters.get_encounter(session, actor, encounter_id)
    rangees = [
        attachments.add_attachment(
            session,
            actor,
            magasin,
            patient,
            fichier.filename or "fichier",
            await fichier.read(),
            encounter_id=encounter_id,
        )
        for fichier in fichiers
    ]
    return [piece_out(p) for p in rangees]


@router.get("/attachments/{attachment_id}/contenu")
def read_attachment(
    attachment_id: UUID, session: SessionDep, actor: ActorDep, magasin: MagasinDep
) -> Response:
    """Rend le fichier tel qu'il a été importé, sans transformation."""
    piece = attachments.get_attachment(session, actor, attachment_id)
    contenu = attachments.read_attachment(magasin, piece)
    return Response(
        content=contenu,
        media_type=piece.media_type,
        headers={"Content-Disposition": f'inline; filename="{piece.filename}"'},
    )


@router.get("/attachments/{attachment_id}/apercu")
def preview_attachment(
    attachment_id: UUID, session: SessionDep, actor: ActorDep, magasin: MagasinDep
) -> Response:
    """Une photo telle qu'un navigateur sait l'afficher : un HEIC d'iPhone sort en JPEG.

    L'original n'est pas touché ; seule cette lecture est convertie.
    """
    from oris_api.services.images import affichable

    piece = attachments.get_attachment(session, actor, attachment_id)
    if not piece.media_type.startswith("image/"):
        raise Unprocessable("NOT_AN_IMAGE", str(attachment_id))
    contenu, media_type = affichable(attachments.read_attachment(magasin, piece), piece.media_type)
    return Response(content=contenu, media_type=media_type)


@router.delete("/attachments/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_attachment(
    attachment_id: UUID, session: SessionDep, actor: ActorDep, magasin: MagasinDep
) -> Response:
    attachments.remove_attachment(session, actor, magasin, attachment_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Correspondants du patient ------------------------------------------------------


@router.get("/{patient_id}/correspondents", response_model=list[RattachementOut])
def list_patient_correspondents(
    patient_id: UUID, session: SessionDep, actor: ActorDep
) -> list[RattachementOut]:
    patients.get_patient(session, actor, patient_id)
    return [
        RattachementOut(role=lien.role, correspondent=CorrespondentOut.model_validate(fiche))
        for lien, fiche in correspondents.rattachements(session, actor, patient_id)
    ]


@router.post("/{patient_id}/correspondents", response_model=list[RattachementOut])
def attach_patient_correspondent(
    patient_id: UUID, body: RattachementIn, session: SessionDep, actor: ActorDep
) -> list[RattachementOut]:
    """Rattacher, ou corriger le rôle si le correspondant est déjà là."""
    patients.get_patient(session, actor, patient_id)
    correspondents.rattacher(session, actor, patient_id, body.correspondent_id, body.role)
    return list_patient_correspondents(patient_id, session, actor)


@router.delete(
    "/{patient_id}/correspondents/{correspondent_id}", status_code=status.HTTP_204_NO_CONTENT
)
def detach_patient_correspondent(
    patient_id: UUID, correspondent_id: UUID, session: SessionDep, actor: ActorDep
) -> None:
    patients.get_patient(session, actor, patient_id)
    correspondents.detacher(session, actor, patient_id, correspondent_id)
