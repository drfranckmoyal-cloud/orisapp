"""Modèles d'échange de l'API (hors objets cliniques, qui viennent des contrats générés)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from oris_api.contracts import ClinicalEncounter, TranscriptSegment
from oris_api.contracts.generated import (
    ClinicalEncounterStatus,
    DocumentDocumentType,
    DocumentStatus,
    LearningEventEventType,
)
from oris_api.domain.corrections import CorrectionOperation
from oris_api.services.audio import GapReason

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class ApiErrorBody(BaseModel):
    code: str
    subject_id: str | None = None
    details: list[str] = []


# Note administrative (§9) : « courte » est une contrainte du cadrage, pas un détail.
# Un champ long inviterait à y écrire du clinique, qu'Oris ne lira jamais.
AdminNote = Annotated[str, StringConstraints(max_length=500)]


class PatientCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    first_name: Name
    last_name: Name
    birth_date: date | None = None
    external_id: str | None = None
    email: Annotated[str, StringConstraints(max_length=200)] = ""
    note: AdminNote = ""


#: Identifiant de dossier SmileCloud : un UUID tel qu'il se lit dans l'adresse du
#: dossier. Contrainte volontairement souple — le jour où SmileCloud change la forme de
#: ses identifiants, mieux vaut un rapprochement qui échoue franchement qu'un champ qui
#: refuse une valeur valable. Mais assez stricte pour écarter un nom collé par erreur.
CaseSmileCloud = Annotated[str, StringConstraints(pattern=r"^[0-9a-fA-F-]{8,64}$")]


class PatientUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    first_name: Name | None = None
    last_name: Name | None = None
    birth_date: date | None = None
    external_id: str | None = None
    email: Annotated[str, StringConstraints(max_length=200)] | None = None
    note: AdminNote | None = None
    # `None` explicite détache le dossier : « ce n'était pas le bon » doit pouvoir se dire.
    smilecloud_case_id: CaseSmileCloud | None = None


class PatientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    first_name: str
    last_name: str
    birth_date: date | None
    external_id: str | None
    smilecloud_case_id: str | None
    email: str
    note: str
    created_at: datetime


class PatientListOut(PatientOut):
    """Le patient **dans la liste** : de quoi le reconnaître sans ouvrir son dossier.

    Une classe à part, et non trois champs de plus sur `PatientOut` : ailleurs ces
    comptes ne sont pas calculés, et un champ à zéro se lirait comme « aucune
    consultation » au lieu de « on n'a pas regardé ».
    """

    consultations: int = 0
    derniere_consultation: datetime | None = None
    a_relire: int = 0


class EncounterCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    patient_id: UUID
    synthetic_case_id: str | None = None
    # Mode ombre : Oris travaille en parallèle, ses sorties ne sont pas utilisables.
    shadow: bool = False


class ProcessingError(BaseModel):
    rule: str
    subject_id: str


class DocumentSummary(BaseModel):
    id: UUID
    document_type: DocumentDocumentType
    status: DocumentStatus
    #: À qui ce document a été envoyé, d'après ce que le praticien a noté (sans doublon).
    sent_to: list[str] = []


class PractitionerOut(BaseModel):
    """Qui a mené la consultation. Un cabinet à plusieurs praticiens doit le voir."""

    id: UUID
    name: str
    title: str


class EncounterOut(BaseModel):
    id: UUID
    patient: PatientOut
    practitioner: PractitionerOut
    status: ClinicalEncounterStatus
    object_version: int
    started_at: datetime | None
    ended_at: datetime | None
    created_at: datetime
    synthetic_case_id: str | None
    mode: str
    processing_errors: list[ProcessingError]
    critical_warning_count: int
    documents: list[DocumentSummary]
    visit_kind: VisitKind = "consultation"


class ClaimOut(BaseModel):
    section: str
    text: str
    fact_ids: list[str]
    warning_codes: list[str]


class ValidationIssueOut(BaseModel):
    code: str
    severity: str
    fact_id: str | None
    claim_index: int | None


class DocumentOut(BaseModel):
    id: UUID
    encounter_id: UUID
    document_type: DocumentDocumentType
    status: DocumentStatus
    version: int
    generated_from_object_version: int
    is_current: bool
    content: str
    claims: list[ClaimOut]
    supported_fact_ids: list[str]
    validation_issues: list[ValidationIssueOut]
    generator: str
    created_at: datetime
    validated_at: datetime | None


class DocumentValidate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    acknowledged_warning_codes: list[str] = []


class CorrectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_object_version: Annotated[int, Field(ge=1)]
    operations: Annotated[list[CorrectionOperation], Field(min_length=1, max_length=20)]
    regenerate: bool = True


class SpokenCorrectionRequest(BaseModel):
    """Correction dictée ou écrite. Par défaut : aperçu, sans rien modifier."""

    model_config = ConfigDict(extra="forbid")
    command: Annotated[str, Field(min_length=1, max_length=500)]
    expected_object_version: Annotated[int, Field(ge=1)] | None = None
    apply: bool = False


class SpokenCorrectionOut(BaseModel):
    """Ce qu'Oris a compris, et ce qu'il a fait — ou pas."""

    kind: Literal["clinical", "editorial", "unclear"]
    summary: str
    impact: Literal["normal", "high"]
    reason: str
    candidates: list[str]
    operations: list[dict[str, Any]]
    applied: bool
    object_version: int


class DocumentTextEdit(BaseModel):
    """Texte réécrit par le praticien (§48)."""

    model_config = ConfigDict(extra="forbid")
    content: Annotated[str, Field(min_length=1, max_length=20_000)]


class ProgressOut(BaseModel):
    """Avancement réel du traitement : chaque nombre est lu en base (S06)."""

    status: ClinicalEncounterStatus
    transcript_segments: int
    facts: int
    documents: int
    termine: bool


class AttachmentOut(BaseModel):
    """Une pièce jointe. Oris ne la lit pas : elle accompagne, elle ne nourrit pas."""

    id: UUID
    filename: str
    media_type: str
    kind: str
    byte_size: int
    label: str
    encounter_id: UUID | None
    created_at: datetime


class DictationOut(BaseModel):
    """Texte dicté, rendu au praticien. Le son n'est jamais conservé."""

    text: str


class LiveSegmentOut(BaseModel):
    """Une parole entendue en direct. Provisoire tant que `is_final` est faux."""

    segment_id: str
    start_ms: int
    end_ms: int
    speaker_role: str
    text: str
    is_final: bool


class LiveTranscriptOut(BaseModel):
    """Ce qu'Oris entend pendant la consultation (§11, §14.1).

    `state` : `disabled` (écoute en direct éteinte), `idle` (pas encore commencée),
    `running`, `stopped`, `failed`. Cette transcription ne sert jamais au dossier.
    """

    state: str
    error_code: str | None = None
    segments: list[LiveSegmentOut]
    total: int
    reconnections: int


class MarkCreate(BaseModel):
    """Point marqué pendant l'écoute : un instant, rien d'autre (spec §11)."""

    timestamp_ms: Annotated[int, Field(ge=0)]


class MarkOut(BaseModel):
    timestamp_ms: int
    created_at: datetime


class ObjectVersionOut(BaseModel):
    version: int
    change_kind: str
    created_at: datetime
    created_by: UUID | None


class TranscriptOut(BaseModel):
    encounter_id: UUID
    segments: list[TranscriptSegment]


class ClinicalObjectOut(BaseModel):
    clinical_object: ClinicalEncounter
    versions: list[ObjectVersionOut]


class LearningEventOut(BaseModel):
    learning_event_id: UUID
    event_type: LearningEventEventType
    scope: str
    source_version: str
    before: Any
    after: Any
    confidence_before: float | None
    validated_by_practitioner: bool
    eligible_for_global_learning: bool
    learning_status: str
    created_at: datetime


class SyntheticCaseOut(BaseModel):
    case_id: str
    domain: str
    tags: list[str]
    patient_first_name: str
    patient_last_name: str
    segment_count: int


VisitKind = Literal["consultation", "procedure"]


class EncounterStart(BaseModel):
    model_config = ConfigDict(extra="forbid")
    patient_informed: bool = False
    #: Choisi avant l'écoute : une consultation ou un acte. Il dit quel modèle de compte
    #: rendu suivre, et quel déroulé afficher pendant l'écoute.
    visit_kind: VisitKind = "consultation"


class EncounterFinish(BaseModel):
    model_config = ConfigDict(extra="forbid")
    final_sequence: Annotated[int, Field(ge=-1)] | None = None
    client_recorded_ms: Annotated[int, Field(ge=0)] | None = None
    accept_gaps: bool = False


class ChunkReceiptOut(BaseModel):
    sequence: int
    status: Literal["stored", "duplicate"]


class AudioGapReport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: GapReason
    duration_ms: Annotated[int, Field(ge=0)] | None = None


class AudioGapOut(BaseModel):
    duration_ms: int | None


class AudioSessionOut(BaseModel):
    status: str
    audio_format: str
    received_count: int
    last_sequence: int | None
    next_sequence: int
    next_timestamp_ms: int
    missing_sequences: list[int]
    received_duration_ms: int
    gaps: list[AudioGapOut]
    reported_gap_reasons: list[str]
    purge_status: str
    finalized_at: datetime | None
    purged_at: datetime | None
    last_received_at: datetime | None


class ClientConfigOut(BaseModel):
    environment: str
    audio_format: str
    sample_rate: int
    chunk_duration_ms: int
    max_chunk_bytes: int
    max_session_minutes: int
    warn_session_minutes: int
    patient_information_mode: Literal["none", "confirm"]
    test_audio_source_enabled: bool
    # Formats de pièces jointes acceptés, et connecteurs disponibles.
    attachment_formats: list[str]
    attachment_max_bytes: int
    smilecloud_connected: bool


class RendezVousOut(BaseModel):
    """Une ligne de l'agenda du jour, telle que l'écran « Votre journée » l'affiche."""

    heure: str
    prenom: str
    nom: str
    motif: str
    statut: str
    smilecloud: Literal["trouve", "absent", "a_verifier", "ambigu", "demande", "inconnu"]
    # Dossier Oris correspondant, s'il existe déjà. `None` veut dire « à créer », et
    # la création reste un geste du praticien : Oris n'ouvre aucun dossier tout seul.
    patient_id: UUID | None = None


class JourneeOut(BaseModel):
    jour: str
    agenda: str
    disponible: bool
    #: Quand l'extension a déposé cette journée. Absent = jamais relevée.
    recu_le: str | None = None
    #: Quand une relecture a été demandée, tant que l'extension ne l'a pas servie.
    demande_le: str | None = None
    #: La dernière tentative de livraison pour ce jour — y compris refusée. Sans elle,
    #: une livraison vide écartée ne se voyait nulle part et l'écran attendait en silence.
    derniere_livraison: LivraisonOut | None = None
    rendezvous: list[RendezVousOut] = []


class LivraisonOut(BaseModel):
    le: str
    rendezvous: int
    #: Faux quand Oris a gardé la journée déjà déposée plutôt que de l'écraser.
    remplace: bool
    raison: str | None = None


class DemandeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    #: Le jour à (re)lire. Absent = aujourd'hui.
    jour: str | None = None


class DemandeOut(BaseModel):
    jour: str
    demande_le: str


class RendezVousDepot(BaseModel):
    """Une ligne telle que l'extension la livre (docs/JOURNEE_DOCTOLIB.md).

    Tolérante : l'extension évolue de son côté, et un champ inconnu de plus ne doit pas
    faire perdre la journée. Seuls `prenom`/`nom` comptent vraiment — une ligne sans nom
    n'est pas un patient (pause, réunion) et sera écartée au rangement.
    """

    model_config = ConfigDict(extra="ignore")
    heure: str = ""
    #: Le nom tel que Doctolib l'écrit (« M. DROIT Justine ») : c'est ce que l'extension
    #: livre. `prenom`/`nom` restent acceptés quand un expéditeur les a déjà séparés.
    patient: str = ""
    prenom: str = ""
    nom: str = ""
    motif: str = ""
    statut: str = ""
    recherche: str = ""


class JourneeDepot(BaseModel):
    model_config = ConfigDict(extra="ignore")
    jour: str
    agenda: str = ""
    rendezvous: list[RendezVousDepot] = []
    #: Ce que l'extension a vu à l'écran. `entetes: false` = tableau non compris ;
    #: une telle livraison ne remplace jamais une journée déjà déposée.
    diagnostic: dict[str, Any] = {}


class DepotOut(BaseModel):
    """Ce qu'on répond à l'extension : ce qui a été gardé, et sinon pourquoi."""

    jour: str
    rendezvous: int
    remplace: bool
    raison: str | None = None


class JourOut(BaseModel):
    """Un jour dans la colonne de gauche : assez pour le colorer, pas plus."""

    jour: str
    lu: bool
    patients: int
    a_creer: int


CorrespondentKind = Literal["practitioner", "organisation"]
#: La civilité n'a de sens que pour une personne, et sert à ouvrir la lettre.
CorrespondentTitle = Literal["", "Dr", "Pr", "M.", "Mme"]
ShortText = Annotated[str, StringConstraints(max_length=200)]


class CorrespondentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    kind: CorrespondentKind
    title: str
    last_name: str
    first_name: str
    specialty: str
    practice: str
    email: str
    phone: str
    secondary_email: str
    secondary_phone: str
    address: str
    note: str
    favorite: bool
    created_at: datetime


class CorrespondentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: CorrespondentKind = "practitioner"
    title: CorrespondentTitle = ""
    #: Le nom, ou la raison sociale quand c'est une structure.
    last_name: Name
    first_name: ShortText = ""
    specialty: Annotated[str, StringConstraints(max_length=80)] = ""
    practice: ShortText = ""
    email: ShortText = ""
    phone: Annotated[str, StringConstraints(max_length=40)] = ""
    secondary_email: ShortText = ""
    secondary_phone: Annotated[str, StringConstraints(max_length=40)] = ""
    address: Annotated[str, StringConstraints(max_length=500)] = ""
    note: Annotated[str, StringConstraints(max_length=500)] = ""
    favorite: bool = False


class CorrespondentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: CorrespondentKind | None = None
    title: CorrespondentTitle | None = None
    last_name: Name | None = None
    first_name: ShortText | None = None
    specialty: Annotated[str, StringConstraints(max_length=80)] | None = None
    practice: ShortText | None = None
    email: ShortText | None = None
    phone: Annotated[str, StringConstraints(max_length=40)] | None = None
    secondary_email: ShortText | None = None
    secondary_phone: Annotated[str, StringConstraints(max_length=40)] | None = None
    address: Annotated[str, StringConstraints(max_length=500)] | None = None
    note: Annotated[str, StringConstraints(max_length=500)] | None = None
    favorite: bool | None = None


class SpecialtyIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: Annotated[str, StringConstraints(min_length=1, max_length=80)]


CorrespondentRole = Literal["referred_by", "referred_to", "also_follows"]


class RattachementOut(BaseModel):
    """Un correspondant du patient, et ce que le lien veut dire."""

    role: CorrespondentRole
    correspondent: CorrespondentOut


class RattachementIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    correspondent_id: UUID
    role: CorrespondentRole


DeliveryChannel = Literal["email", "mail", "hand", "secure_messaging", "other"]
DeliveryRecipient = Literal["patient", "correspondent", "other"]


class DeliveryIn(BaseModel):
    """Noter un envoi. Oris n'envoie rien : il retient ce que le praticien a envoyé."""

    model_config = ConfigDict(extra="forbid")
    recipient_kind: DeliveryRecipient
    channel: DeliveryChannel
    correspondent_id: UUID | None = None
    recipient_label: Annotated[str, Field(max_length=200)] = ""


class DeliveryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    document_id: UUID
    recipient_kind: DeliveryRecipient
    correspondent_id: UUID | None
    recipient_label: str
    channel: DeliveryChannel
    sent_at: datetime


class FigureIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    attachment_id: UUID
    caption: Annotated[str, Field(max_length=300)] = ""


class FiguresIn(BaseModel):
    """La liste entière, dans l'ordre d'impression."""

    model_config = ConfigDict(extra="forbid")
    figures: Annotated[list[FigureIn], Field(max_length=12)]


class FigureOut(BaseModel):
    attachment_id: UUID
    caption: str
    position: int
    filename: str
    media_type: str


class EtapeOut(BaseModel):
    titre: str
    rang: int | None
    dents: list[str]
    details: list[str]
    statut: str
    delai: str | None
    couleur: int
    fact_ids: list[str]


class PlanVueOut(BaseModel):
    """Le plan mis en forme : étapes, chronologie, écartés, dents absentes du schéma."""

    numerote: bool
    etapes: list[EtapeOut]
    ecartes: list[EtapeOut]
    dents_absentes: list[str]
