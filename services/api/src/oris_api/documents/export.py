"""Sortie d'un document : PDF A4 et texte pour le dossier patient (spec §78–79).

Rien n'est reformulé ici : le contenu vient du document déjà rédigé depuis l'objet
clinique. Cette couche ajoute seulement l'en-tête réglementaire (qui, pour qui, quand,
quoi) et dit franchement si le document a été validé par le praticien.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen.canvas import Canvas

from oris_api.documents.renderer import LIMITS_SECTION, SECTION_ORDER

SECTION_TITLES = frozenset(
    {section for section, _ in SECTION_ORDER} | {LIMITS_SECTION, "Plan de traitement"}
)

DOCUMENT_TITLES = {
    "consultation_note": "Compte rendu de consultation",
    "treatment_plan_text": "Plan de traitement",
    "operative_note": "Compte rendu opératoire",
    "patient_summary": "Résumé pour le patient",
    "referral_letter": "Courrier d'adressage",
}
DRAFT_NOTICE = "Brouillon — non validé par le praticien."
VALIDATED_NOTICE = "Validé par le praticien le {date}."
FOOTER = "Établi avec Oris · {page}/{total}"

MARGIN = 20 * mm
TITLE_SIZE = 15
BODY_SIZE = 10.5
HEADING_SIZE = 11
LINE = 5.6 * mm


@dataclass(frozen=True)
class ExportContext:
    """Ce qui identifie le document, en dehors de son contenu."""

    document_type: str
    content: str
    practitioner: str
    organization: str
    patient: str
    encounter_date: datetime
    validated_at: datetime | None
    version: int


def french_date(moment: datetime) -> str:
    return moment.strftime("%d/%m/%Y")


def french_datetime(moment: datetime) -> str:
    return moment.strftime("%d/%m/%Y à %H:%M")


def title_for(document_type: str) -> str:
    return DOCUMENT_TITLES.get(document_type, document_type)


def notice_for(context: ExportContext) -> str:
    if context.validated_at is None:
        return DRAFT_NOTICE
    return VALIDATED_NOTICE.format(date=french_datetime(context.validated_at))


def header_lines(context: ExportContext) -> list[str]:
    return [
        f"{context.organization} — {context.practitioner}",
        f"Patient : {context.patient}",
        f"Consultation du {french_date(context.encounter_date)}",
        f"{title_for(context.document_type)} (version {context.version})",
        notice_for(context),
    ]


def render_text(context: ExportContext, structured: bool) -> str:
    """Texte à coller dans le logiciel métier : brut, ou précédé de l'en-tête."""
    if not structured:
        return context.content.strip() + "\n"
    return "\n".join([*header_lines(context), "", context.content.strip(), ""])


def is_heading(line: str) -> bool:
    """Intitulé de section : la liste vient du rédacteur, elle n'est pas devinée."""
    return line in SECTION_TITLES


def wrap(text: str, font: str, size: float, width: float) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if stringWidth(candidate, font, size) <= width:
            current = candidate
            continue
        if current:
            lines.append(current)
        current = word
    lines.append(current)
    return lines or [""]


def render_pdf(context: ExportContext) -> bytes:
    """PDF A4 : en-tête d'identification, contenu, mention de validation, pagination."""
    buffer = io.BytesIO()
    canvas = Canvas(buffer, pagesize=A4)
    canvas.setTitle(title_for(context.document_type))
    canvas.setAuthor(context.practitioner)
    width, height = A4
    usable = width - 2 * MARGIN

    pages: list[list[tuple[str, str]]] = [[]]
    room = height - MARGIN - 42 * mm  # première page : sous l'en-tête
    used = 0.0
    for raw in context.content.strip().splitlines():
        line = raw.strip()
        if not line:
            pages[-1].append(("space", ""))
            used += LINE / 2
            continue
        style = "heading" if is_heading(line) else "body"
        size = HEADING_SIZE if style == "heading" else BODY_SIZE
        font = "Helvetica-Bold" if style == "heading" else "Helvetica"
        for piece in wrap(line, font, size, usable):
            if used + LINE > room:
                pages.append([])
                room = height - 2 * MARGIN
                used = 0.0
            pages[-1].append((style, piece))
            used += LINE

    total = len(pages)
    for number, page in enumerate(pages, start=1):
        y = height - MARGIN
        if number == 1:
            canvas.setFont("Helvetica-Bold", TITLE_SIZE)
            canvas.drawString(MARGIN, y, title_for(context.document_type))
            y -= 9 * mm
            canvas.setFont("Helvetica", 9)
            for line in header_lines(context)[:-1]:
                canvas.drawString(MARGIN, y, line)
                y -= 4.6 * mm
            canvas.setFont("Helvetica-Oblique", 9)
            canvas.drawString(MARGIN, y, notice_for(context))
            y -= 6 * mm
            canvas.line(MARGIN, y, width - MARGIN, y)
            y -= 8 * mm
        for style, line in page:
            if style == "space":
                y -= LINE / 2
                continue
            canvas.setFont(
                "Helvetica-Bold" if style == "heading" else "Helvetica",
                HEADING_SIZE if style == "heading" else BODY_SIZE,
            )
            canvas.drawString(MARGIN, y, line)
            y -= LINE
        canvas.setFont("Helvetica", 8)
        canvas.drawCentredString(width / 2, MARGIN / 2, FOOTER.format(page=number, total=total))
        canvas.showPage()
    canvas.save()
    return buffer.getvalue()
