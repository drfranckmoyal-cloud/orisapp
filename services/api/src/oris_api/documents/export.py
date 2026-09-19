"""Sortie d'un document : PDF habillé et texte pour le dossier patient (spec §78–79).

Rien n'est reformulé ici : le contenu vient du document déjà rédigé depuis l'objet
clinique. Cette couche ajoute l'en-tête réglementaire (qui, pour qui, quand, quoi),
dit franchement si le document a été validé, et choisit la **mise en page du type de
document** : un courrier à un confrère ne se présente pas comme un résumé remis au
patient.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen.canvas import Canvas

from oris_api.documents.operative_templates import SECTIONS as OPERATIVE_SECTIONS
from oris_api.documents.renderer import LIMITS_SECTION, SECTION_ORDER
from oris_api.documents.theme import Cabinet, color

# Les intitulés de section ne sont pas devinés à la mise en page : ils viennent des
# rédacteurs (compte rendu de consultation, plan, modèles opératoires).
SECTION_TITLES = frozenset(
    {section for section, _ in SECTION_ORDER}
    | set(OPERATIVE_SECTIONS)
    | {LIMITS_SECTION, "Plan de traitement", "Acte réalisé", "Acte prévu"}
)

DRAFT_NOTICE = "Brouillon — non validé par le praticien."
VALIDATED_NOTICE = "Validé par le praticien le {date}."
FOOTER = "Établi avec Oris · {page}/{total}"

MARGIN = 20 * mm
LOGO_HEIGHT = 9 * mm
LOGO_MAX_WIDTH = 46 * mm


@dataclass(frozen=True)
class Layout:
    """Ce qui distingue un type de document à l'impression."""

    title: str
    body_size: float = 10.5
    heading_size: float = 11
    leading: float = 5.6 * mm
    letter: bool = False  # formules d'appel et de politesse
    closing: str = ""
    salutation: str = ""
    intro: str = ""
    footer_note: str = ""


LAYOUTS: dict[str, Layout] = {
    "consultation_note": Layout(title="Compte rendu de consultation"),
    "treatment_plan_text": Layout(title="Plan de traitement"),
    "operative_note": Layout(title="Compte rendu de soins"),
    "referral_letter": Layout(
        title="Courrier d'adressage",
        letter=True,
        salutation="Chère Consœur, Cher Confrère,",
        closing="Confraternellement,",
    ),
    "patient_summary": Layout(
        title="Votre consultation",
        body_size=12,
        heading_size=12.5,
        leading=7 * mm,
        intro="Ce document résume ce qui a été vu et décidé aujourd'hui.",
        footer_note=("Remis à titre d'information. En cas de question, contactez le cabinet."),
    ),
}
DEFAULT_LAYOUT = Layout(title="Document")


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


def layout_for(document_type: str) -> Layout:
    return LAYOUTS.get(document_type, DEFAULT_LAYOUT)


def title_for(document_type: str) -> str:
    return layout_for(document_type).title


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


Block = tuple[str, str]


def body_blocks(context: ExportContext, layout: Layout, usable: float) -> list[Block]:
    """Le contenu découpé en lignes prêtes à poser, avec leur style."""
    blocks: list[Block] = []
    if layout.intro:
        blocks += [
            ("muted", piece) for piece in wrap(layout.intro, "Helvetica-Oblique", 10, usable)
        ]
        blocks.append(("space", ""))
    if layout.salutation:
        blocks.append(("body", layout.salutation))
        blocks.append(("space", ""))
    for raw in context.content.strip().splitlines():
        line = raw.strip()
        if not line:
            blocks.append(("space", ""))
            continue
        style = "heading" if is_heading(line) else "body"
        font = "Helvetica-Bold" if style == "heading" else "Helvetica"
        size = layout.heading_size if style == "heading" else layout.body_size
        blocks += [(style, piece) for piece in wrap(line, font, size, usable)]
    if layout.closing:
        blocks += [
            ("space", ""),
            ("body", layout.closing),
            ("space", ""),
            ("body", context.practitioner),
        ]
    return blocks


def draw_logo(canvas: Canvas, cabinet: Cabinet, x: float, top: float) -> float:
    """Dessine le logo s'il y en a un ; renvoie la hauteur occupée."""
    if cabinet.logo is None:
        return 0.0
    image = ImageReader(str(cabinet.logo))
    width, height = image.getSize()
    drawn_width = min(LOGO_MAX_WIDTH, LOGO_HEIGHT * width / height)
    drawn_height = drawn_width * height / width
    canvas.drawImage(
        image, x, top - drawn_height, width=drawn_width, height=drawn_height, mask="auto"
    )
    return drawn_height


def draw_letterhead(
    canvas: Canvas,
    context: ExportContext,
    layout: Layout,
    cabinet: Cabinet,
    width: float,
    top: float,
) -> float:
    """En-tête : logo et cabinet à gauche, identité du document à droite."""
    logo_height = draw_logo(canvas, cabinet, MARGIN, top)
    y = top - logo_height - (3 * mm if logo_height else 0)

    canvas.setFillColor(color("title"))
    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawString(MARGIN, y, cabinet.name)
    y -= 4.4 * mm
    canvas.setFillColor(color("muted"))
    canvas.setFont("Helvetica", 8.5)
    for line in cabinet.contact_lines():
        canvas.drawString(MARGIN, y, line)
        y -= 3.8 * mm

    # Colonne de droite : praticien, patient, date.
    right = top - (2 * mm)
    canvas.setFillColor(color("body"))
    canvas.setFont("Helvetica", 9)
    title = f"{cabinet.practitioner_title} {context.practitioner}".strip()
    for line in (
        title,
        f"Patient : {context.patient}",
        f"Le {french_date(context.encounter_date)}",
    ):
        canvas.drawRightString(width - MARGIN, right, line)
        right -= 4.4 * mm

    y = min(y, right) - 3 * mm
    canvas.setStrokeColor(color("rule"))
    canvas.setLineWidth(0.8)
    canvas.line(MARGIN, y, width - MARGIN, y)
    y -= 9 * mm

    canvas.setFillColor(color("title"))
    canvas.setFont("Helvetica-Bold", 16)
    heading = layout.title
    if layout.title == "Votre consultation":
        heading = f"Votre consultation du {french_date(context.encounter_date)}"
    canvas.drawString(MARGIN, y, heading)
    y -= 5.5 * mm

    canvas.setFont("Helvetica-Oblique", 8.5)
    canvas.setFillColor(color("muted") if context.validated_at else color("accent"))
    canvas.drawString(MARGIN, y, f"{notice_for(context)} Version {context.version}.")
    return y - 8 * mm


def draw_footer(
    canvas: Canvas, layout: Layout, cabinet: Cabinet, width: float, page: int, total: int
) -> None:
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(color("muted"))
    canvas.drawString(MARGIN, MARGIN / 2, cabinet.name)
    canvas.drawRightString(width - MARGIN, MARGIN / 2, FOOTER.format(page=page, total=total))
    if layout.footer_note and page == total:
        canvas.drawCentredString(width / 2, MARGIN / 2 + 4.5 * mm, layout.footer_note)


def render_pdf(context: ExportContext, cabinet: Cabinet | None = None) -> bytes:
    """PDF A4 habillé, mis en page selon le type de document."""
    cabinet = cabinet or Cabinet.load()
    layout = layout_for(context.document_type)
    buffer = io.BytesIO()
    canvas = Canvas(buffer, pagesize=A4)
    canvas.setTitle(layout.title)
    canvas.setAuthor(context.practitioner)
    width, height = A4
    usable = width - 2 * MARGIN

    blocks = body_blocks(context, layout, usable)
    first_page_top = height - MARGIN - 52 * mm  # sous l'en-tête complet
    other_pages_top = height - MARGIN - 8 * mm

    pages: list[list[Block]] = [[]]
    room = first_page_top
    used = 0.0
    for style, line in blocks:
        step = layout.leading / 2 if style == "space" else layout.leading
        if used + step > room:
            pages.append([])
            room = other_pages_top
            used = 0.0
            if style == "space":
                continue
        pages[-1].append((style, line))
        used += step

    total = len(pages)
    for number, page in enumerate(pages, start=1):
        y = height - MARGIN
        if number == 1:
            y = draw_letterhead(canvas, context, layout, cabinet, width, y)
        else:
            canvas.setFont("Helvetica", 8.5)
            canvas.setFillColor(color("muted"))
            canvas.drawString(MARGIN, y, f"{layout.title} — {context.patient}")
            y -= 8 * mm
        for style, line in page:
            if style == "space":
                y -= layout.leading / 2
                continue
            if style == "heading":
                canvas.setFont("Helvetica-Bold", layout.heading_size)
                canvas.setFillColor(color("heading"))
            elif style == "muted":
                canvas.setFont("Helvetica-Oblique", 10)
                canvas.setFillColor(color("muted"))
            else:
                canvas.setFont("Helvetica", layout.body_size)
                canvas.setFillColor(color("body"))
            canvas.drawString(MARGIN, y, line)
            y -= layout.leading
        draw_footer(canvas, layout, cabinet, width, number, total)
        canvas.showPage()
    canvas.save()
    return buffer.getvalue()
