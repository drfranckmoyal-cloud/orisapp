"""Génération, invalidation et validation des documents (spec §50, D008, D009)."""

from __future__ import annotations

from collections.abc import Collection, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from functools import partial
from typing import Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from oris_api.contracts import ClinicalEncounter
from oris_api.contracts.generated import DocumentDocumentType
from oris_api.db.models import (
    Correspondent,
    DocumentRow,
    DocumentVersion,
    Encounter,
    Organization,
    Patient,
    PatientCorrespondent,
    User,
)
from oris_api.documents.export import ExportContext, render_pdf, render_text
from oris_api.documents.renderer import Style
from oris_api.documents.theme import Cabinet
from oris_api.domain.preferences import PractitionerPreferences
from oris_api.domain.types import GeneratedDocument, ValidationIssue
from oris_api.providers import ProviderSet
from oris_api.services import async_bridge, audit, figures, learning
from oris_api.services.attachments import Magasin
from oris_api.services.clinical_store import load_current
from oris_api.services.errors import Conflict, NotFound
from oris_api.services.identity import Actor

VALIDATABLE = frozenset({"draft_ai", "needs_review"})


def operative_note_available(obj: ClinicalEncounter) -> bool:
    """Un acte non annulé a été dit : un compte rendu de soins est possible (§81)."""
    return any(procedure.status != "cancelled" for procedure in obj.procedures)


def document_types_for(
    obj: ClinicalEncounter, existing: Collection[str] = ()
) -> list[DocumentDocumentType]:
    """Documents que l'objet justifie.

    Le compte rendu de soins n'est jamais produit d'office (§81 : le praticien le
    demande) — mais une fois demandé, il se régénère comme les autres.
    """
    types: list[DocumentDocumentType] = ["consultation_note"]
    if obj.treatment_plan is not None and obj.treatment_plan.items:
        types.append("treatment_plan_text")
    if "operative_note" in existing and operative_note_available(obj):
        types.append("operative_note")
    # Le courrier d'adressage, lui aussi, n'existe que demandé ; il suit ensuite les
    # corrections comme les autres.
    if "referral_letter" in existing and obj.facts:
        types.append("referral_letter")
    return types


async def generate_and_check(
    providers: ProviderSet,
    obj: ClinicalEncounter,
    document_type: DocumentDocumentType,
    style: Style | None = None,
    synthetic: bool = False,
) -> tuple[GeneratedDocument, list[ValidationIssue]]:
    writer = providers.synthetic_document_generation if synthetic else providers.document_generation
    generated = await writer.generate(obj, document_type, style)
    return generated, await providers.clinical_validation.validate(generated, obj)


def list_documents(session: Session, encounter_id: UUID) -> list[DocumentRow]:
    return list(
        session.scalars(
            select(DocumentRow)
            .where(DocumentRow.encounter_id == encounter_id)
            .order_by(DocumentRow.document_type)
        )
    )


def current_version(session: Session, document: DocumentRow) -> DocumentVersion | None:
    if document.current_version_id is None:
        return None
    return session.get(DocumentVersion, document.current_version_id)


def generate(
    session: Session,
    encounter: Encounter,
    obj: ClinicalEncounter,
    providers: ProviderSet,
    include: Sequence[DocumentDocumentType] = (),
) -> list[DocumentRow]:
    """Produit une nouvelle version de chaque document pour la version d'objet donnée.

    `include` : documents demandés explicitement par le praticien, en plus de ceux que
    l'objet justifie de lui-même.
    """
    # Préférences de rédaction du praticien : la forme lui appartient, le fond non.
    preferences = PractitionerPreferences.load(
        (session.get(User, encounter.practitioner_id) or User()).preferences
    )
    style = Style(length=preferences.document_length, terminology=dict(preferences.terminology))
    existing = {doc.document_type: doc for doc in list_documents(session, encounter.id)}
    wanted = document_types_for(obj, {*existing, *include})
    produced: list[DocumentRow] = []

    # Une consultation fictive ne sort jamais d'Oris, pas même ses faits.
    synthetic = isinstance(encounter.metadata_json.get("synthetic_case_id"), str)
    for document_type in wanted:
        generated, issues = async_bridge.run(
            partial(generate_and_check, providers, obj, document_type, style, synthetic)
        )
        document = existing.get(document_type)
        if document is None:
            document = DocumentRow(
                encounter_id=encounter.id, document_type=document_type, status="draft_ai"
            )
            session.add(document)
            session.flush()
        last = current_version(session, document)
        info = providers.document_generation.info
        version = DocumentVersion(
            document_id=document.id,
            version=(last.version + 1) if last else 1,
            content=generated.content,
            claims=[
                {
                    **asdict(claim),
                    "fact_ids": list(claim.fact_ids),
                    "warning_codes": list(claim.warning_codes),
                }
                for claim in generated.claims
            ],
            supported_fact_ids=generated.supported_fact_ids,
            validation_issues=[asdict(issue) for issue in issues],
            generated_from_object_version=obj.object_version,
            generator=generated.generator or f"{info.name}:{info.version}",
        )
        session.add(version)
        session.flush()
        document.current_version_id = version.id
        document.status = "needs_review" if issues else "draft_ai"
        audit.record(
            session,
            None,
            "document.generated",
            "document",
            document.id,
            organization_id=encounter.organization_id,
            object_version=obj.object_version,
            version=version.version,
        )
        produced.append(document)

    # Un document dont l'objet ne justifie plus l'existence (plan vidé) est remplacé.
    for existing_type, existing_document in existing.items():
        if existing_type not in wanted and existing_document.status != "superseded":
            existing_document.status = "superseded"
    session.flush()
    return produced


def mark_outdated(session: Session, encounter_id: UUID) -> None:
    encounter = session.get(Encounter, encounter_id)
    organization_id = encounter.organization_id if encounter else None
    for document in list_documents(session, encounter_id):
        if document.status != "superseded":
            document.status = "outdated"
            audit.record(
                session,
                None,
                "document.outdated",
                "document",
                document.id,
                organization_id=organization_id,
            )
    session.flush()


def edit_text(session: Session, actor: Actor, document_id: UUID, content: str) -> DocumentRow:
    """Édition manuelle du texte par le praticien (§48).

    Oris ne touche pas au dossier clinique : le texte devient celui du praticien, et il
    est dit tel quel. La provenance phrase par phrase n'est plus disponible sur un texte
    écrit à la main — l'interface doit le signaler plutôt que de faire semblant.
    """
    document = session.get(DocumentRow, document_id)
    encounter = session.get(Encounter, document.encounter_id) if document else None
    if document is None or encounter is None or encounter.organization_id != actor.organization_id:
        raise NotFound("DOCUMENT_NOT_FOUND", str(document_id))
    if encounter.mode == "shadow":
        raise Conflict("SHADOW_ENCOUNTER", str(document_id))
    last = current_version(session, document)
    if last is None:
        raise Conflict("DOCUMENT_EMPTY", str(document_id))
    if content.strip() == last.content.strip():
        raise Conflict("NO_CHANGE", str(document_id))

    version = DocumentVersion(
        document_id=document.id,
        version=last.version + 1,
        content=content.strip(),
        claims=[],
        supported_fact_ids=[],
        validation_issues=[],
        generated_from_object_version=last.generated_from_object_version,
        generator="practitioner:manual",
    )
    session.add(version)
    session.flush()
    document.current_version_id = version.id
    document.status = "draft_ai" if document.status == "outdated" else document.status
    learning.emit(
        session,
        actor,
        encounter.id,
        last.generated_from_object_version,
        "document_text_edit",
        {"document_type": document.document_type, "longueur": len(last.content)},
        {"document_type": document.document_type, "longueur": len(content.strip())},
    )
    audit.record(
        session,
        actor,
        "document.edited",
        "document",
        document.id,
        version=version.version,
    )
    session.flush()
    return document


def validate(
    session: Session,
    actor: Actor,
    document_id: UUID,
    acknowledged_warning_codes: list[str],
) -> DocumentRow:
    """Validation explicite du praticien : jamais automatique (D009)."""
    document = session.get(DocumentRow, document_id)
    encounter = session.get(Encounter, document.encounter_id) if document else None
    if document is None or encounter is None or encounter.organization_id != actor.organization_id:
        raise NotFound("DOCUMENT_NOT_FOUND", str(document_id))
    version = current_version(session, document)
    if version is None:
        raise Conflict("DOCUMENT_EMPTY", str(document_id))
    if encounter.mode == "shadow":
        # M11 : une sortie d'ombre ne devient jamais un document clinique.
        raise Conflict("SHADOW_ENCOUNTER", str(document_id))
    if document.status == "validated":
        raise Conflict("DOCUMENT_ALREADY_VALIDATED", str(document_id))
    obj = load_current(session, encounter)
    if (
        document.status not in VALIDATABLE
        or version.generated_from_object_version != obj.object_version
    ):
        raise Conflict("DOCUMENT_OUTDATED", str(document_id))
    if any(issue["severity"] == "critical" for issue in version.validation_issues):
        raise Conflict("DOCUMENT_HAS_CRITICAL_ISSUES", str(document_id))
    critical = sorted({w.code for w in obj.warnings if w.severity == "critical"})
    missing = [code for code in critical if code not in acknowledged_warning_codes]
    if missing:
        raise Conflict("WARNING_NOT_ACKNOWLEDGED", str(document_id), details=missing)

    document.status = "validated"
    version.validated_at = datetime.now(UTC)
    version.validated_by = actor.user_id
    version.acknowledged_warning_codes = critical
    for code in critical:
        learning.emit(
            session,
            actor,
            encounter.id,
            obj.object_version,
            "warning_confirmed",
            None,
            {"warning_code": code, "document_type": document.document_type},
        )
    # M1 n'a pas d'édition de texte : toute validation est « sans modification » (§127).
    learning.emit(
        session,
        actor,
        encounter.id,
        obj.object_version,
        "document_validated_unchanged",
        None,
        {"document_type": document.document_type, "document_version": version.version},
    )
    audit.record(
        session, actor, "document.validated", "document", document.id, version=version.version
    )
    session.flush()
    return document


ExportFormat = Literal["pdf", "text", "structured"]
EXPORT_MEDIA = {
    "pdf": "application/pdf",
    "text": "text/plain; charset=utf-8",
    "structured": "text/plain; charset=utf-8",
}
EXPORT_FILENAMES = {
    "consultation_note": "compte-rendu",
    "treatment_plan_text": "plan-de-traitement",
    "operative_note": "compte-rendu-operatoire",
    "patient_summary": "resume-patient",
    "referral_letter": "courrier-adressage",
}


@dataclass(frozen=True)
class ExportedDocument:
    payload: bytes
    media_type: str
    filename: str


def export_document(
    session: Session,
    actor: Actor,
    document_id: UUID,
    fmt: ExportFormat,
    magasin: Magasin | None = None,
) -> ExportedDocument:
    """Sortie d'un document pour le dossier patient.

    Un brouillon peut sortir, mais il part en portant sa mention « non validé » et son
    statut ne bouge pas : seule la sortie d'un document validé le passe à `exported`
    (spec §50 : la validation reste une action explicite du praticien).
    """
    document = session.get(DocumentRow, document_id)
    encounter = session.get(Encounter, document.encounter_id) if document else None
    if document is None or encounter is None or encounter.organization_id != actor.organization_id:
        raise NotFound("DOCUMENT_NOT_FOUND", str(document_id))
    version = current_version(session, document)
    if version is None:
        raise Conflict("DOCUMENT_EMPTY", str(document_id))
    if encounter.mode == "shadow":
        raise Conflict("SHADOW_ENCOUNTER", str(document_id))

    patient = session.get(Patient, encounter.patient_id)
    practitioner = session.get(User, encounter.practitioner_id)
    organization = session.get(Organization, encounter.organization_id)
    cabinet = Cabinet.from_identity(
        dict(organization.identity or {}) if organization else {},
        organization.name if organization else "",
    )
    adresse_par, destinataire = _correspondants_du_document(session, encounter)
    photos = figures.a_imprimer(session, magasin, document.id) if magasin and fmt == "pdf" else ()
    vue_plan = None
    if document.document_type == "treatment_plan_text" and fmt == "pdf":
        from oris_api.documents.plan import plan_vue
        from oris_api.services.clinical_store import load_current

        vue_plan = plan_vue(load_current(session, encounter))
    context = ExportContext(
        plan=vue_plan,
        figures=photos,
        referred_by=adresse_par,
        recipient=destinataire,
        document_type=document.document_type,
        content=version.content,
        practitioner=practitioner.name if practitioner else "Praticien",
        organization=cabinet.name,
        patient=f"{patient.first_name} {patient.last_name}" if patient else "Patient",
        encounter_date=encounter.started_at or encounter.created_at,
        validated_at=version.validated_at,
        version=version.version,
    )
    if fmt == "pdf":
        payload = render_pdf(context, cabinet)
    else:
        payload = render_text(context, structured=fmt == "structured").encode("utf-8")

    # Le nom du fichier ne porte pas le patient : il vivrait dans un dossier de
    # téléchargements, hors du dossier clinique. L'identité est dans le document.
    suffix = "pdf" if fmt == "pdf" else "txt"
    stamp = context.encounter_date.strftime("%Y-%m-%d")
    filename = f"oris-{EXPORT_FILENAMES.get(document.document_type, 'document')}-{stamp}.{suffix}"

    audit.record(
        session,
        actor,
        "document.exported",
        "document",
        document.id,
        format=fmt,
        document_status=document.status,
    )
    if document.status == "validated":
        document.status = "exported"
        mark_encounter_exported(session, actor, encounter)
    session.flush()
    return ExportedDocument(payload=payload, media_type=EXPORT_MEDIA[fmt], filename=filename)


def mark_encounter_exported(session: Session, actor: Actor, encounter: Encounter) -> None:
    """La consultation passe à `exported` quand tous ses documents en sont sortis."""
    from oris_api.services.encounters import transition

    active = [d for d in list_documents(session, encounter.id) if d.status != "superseded"]
    if encounter.status == "validated" and active and all(d.status == "exported" for d in active):
        transition(session, actor, encounter, "exported")


def _nom_correspondant(fiche: Correspondent) -> str:
    """« Dr Claire Martin · ODF » ; une structure garde son seul nom."""
    if fiche.kind == "organisation":
        return fiche.last_name
    parts = (fiche.title, fiche.first_name, fiche.last_name)
    nom = " ".join(part.strip() for part in parts if part.strip())
    return f"{nom} · {fiche.specialty}" if fiche.specialty else nom


def _correspondants_du_document(session: Session, encounter: Encounter) -> tuple[str, str]:
    """Qui a adressé ce patient, et à qui on l'adresse — depuis sa fiche.

    Rien n'est deviné : sans correspondant rattaché, la ligne disparaît du document.
    """
    liens = session.execute(
        select(PatientCorrespondent.role, Correspondent)
        .join(Correspondent, Correspondent.id == PatientCorrespondent.correspondent_id)
        .where(PatientCorrespondent.patient_id == encounter.patient_id)
        .order_by(PatientCorrespondent.created_at)
    ).all()
    par = next((_nom_correspondant(c) for role, c in liens if role == "referred_by"), "")
    vers = next((_nom_correspondant(c) for role, c in liens if role == "referred_to"), "")
    return par, vers
