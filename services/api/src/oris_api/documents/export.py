"""Sortie d'un document : PDF habillé et texte pour le dossier patient (spec §78–79).

Rien n'est reformulé ici : le contenu vient du document déjà rédigé depuis l'objet
clinique. Cette couche ajoute l'en-tête réglementaire (qui, pour qui, quand, quoi),
dit franchement si le document a été validé, et choisit la **mise en page du type de
document** : un courrier à un confrère ne se présente pas comme un résumé remis au
patient.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen.canvas import Canvas

from oris_api.documents.operative_templates import SECTIONS as OPERATIVE_SECTIONS
from oris_api.documents.renderer import (
    LIMITS_SECTION,
    RUBRIQUES_CONSULTATION,
    RUBRIQUES_COURRIER,
    RUBRIQUES_OPERATOIRE,
    SECTION_ORDER,
)
from oris_api.documents.theme import Cabinet, color

# Les intitulés de section ne sont pas devinés à la mise en page : ils viennent des
# rédacteurs (compte rendu de consultation, plan, modèles opératoires).
SECTION_TITLES = frozenset(
    {section for section, _ in SECTION_ORDER}
    | set(RUBRIQUES_CONSULTATION)
    | set(RUBRIQUES_OPERATOIRE)
    | set(RUBRIQUES_COURRIER)
    | set(OPERATIVE_SECTIONS)
    | {LIMITS_SECTION, "Plan de traitement", "Acte réalisé", "Acte prévu"}
)

DRAFT_NOTICE = "Brouillon — non validé par le praticien."
VALIDATED_NOTICE = "Validé par le praticien le {date}."
# Numéro seul : la page de photos, posée après coup, fausserait un « n/N ».
FOOTER = "{page}"

MARGIN = 20 * mm
LOGO_HEIGHT = 9 * mm
LOGO_MAX_WIDTH = 46 * mm
#: Le monogramme du praticien, à côté du nom : la hauteur du nom et de ses titres.
LOGO_ENTETE = 20 * mm


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
    date_label: str = "Date de consultation"
    #: Les phrases d'une rubrique coulent en un paragraphe (compte rendu rédigé) ;
    #: sinon une ligne par élément (plan de traitement, acte).
    paragraphs: bool = False


LAYOUTS: dict[str, Layout] = {
    "consultation_note": Layout(title="Compte rendu de consultation", paragraphs=True),
    "treatment_plan_text": Layout(title="Plan de traitement"),
    "operative_note": Layout(title="Compte rendu opératoire", date_label="Date de l’intervention"),
    "referral_letter": Layout(
        title="Courrier d’adressage",
        letter=True,
        salutation="Cher confrère,",
        paragraphs=True,
        closing="Bien confraternellement,",
        date_label="Date du courrier",
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
    #: « Dr Claire Martin · ODF » : le correspondant qui a adressé le patient.
    referred_by: str = ""
    #: Pour un courrier : le confrère à qui il est adressé.
    recipient: str = ""
    #: Photos de la « Documentation clinique » (contenu, légende), dans l'ordre choisi.
    figures: tuple[Any, ...] = ()


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


def paragraph_lines(content: str, paragraphs: bool) -> list[str]:
    """Les lignes du contenu ; en mode paragraphe, les phrases d'une rubrique sont jointes."""
    lines = content.strip().splitlines()
    if not paragraphs:
        return lines
    joined: list[str] = []
    for raw in lines:
        line = raw.strip()
        previous = joined[-1] if joined else ""
        if line and previous and not is_heading(line) and not is_heading(previous):
            joined[-1] = f"{previous} {line}"
        else:
            joined.append(line)
    return joined


def body_blocks(context: ExportContext, layout: Layout, usable: float) -> list[Block]:
    """Le contenu découpé en lignes prêtes à poser, avec leur style."""
    blocks: list[Block] = []
    if layout.intro:
        blocks += [("muted", piece) for piece in wrap(layout.intro, "Times-Italic", 10.5, usable)]
        blocks.append(("space", ""))
    if layout.salutation:
        blocks.append(("body", layout.salutation))
        blocks.append(("space", ""))
    for raw in paragraph_lines(context.content, layout.paragraphs):
        line = raw.strip()
        if not line:
            blocks.append(("space", ""))
            continue
        style = "heading" if is_heading(line) else "body"
        font = "Times-Roman"
        size = layout.heading_size + 3 if style == "heading" else layout.body_size + 0.5
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


# Polices du modèle : un romain à empattements, comme les fichiers Word du praticien.
SERIF = "Times-Roman"
SERIF_GRAS = "Times-Bold"
SERIF_ITALIQUE = "Times-Italic"


def signature(context: ExportContext, cabinet: Cabinet) -> str:
    """« Dr Franck Moyal » — sans doubler le titre s'il est déjà dans le nom."""
    titre = cabinet.practitioner_title.strip()
    if not titre or context.practitioner.startswith(f"{titre} "):
        return context.practitioner
    return f"{titre} {context.practitioner}"


def patient_rows(context: ExportContext, layout: Layout) -> list[tuple[str, str]]:
    """Le bloc patient du modèle. Une ligne sans valeur n'existe pas."""
    rows = [
        ("Patient(e)", context.patient),
        (layout.date_label, french_date(context.encounter_date)),
    ]
    if layout.letter:
        rows.append(("Destinataire", context.recipient))
    else:
        rows.append(("Adressé(e) par", context.referred_by))
    return [(label, value) for label, value in rows if value]


def draw_letterhead(
    canvas: Canvas,
    context: ExportContext,
    layout: Layout,
    cabinet: Cabinet,
    width: float,
    top: float,
) -> float:
    """En-tête : logo à côté du nom, titres, puis RPPS et coordonnées ; titre, bloc patient.

    Tout est aligné à gauche, sous le nom : l'identité se lit d'un seul regard.
    """
    x = MARGIN
    logo_height = 0.0
    if cabinet.logo is not None:
        image = ImageReader(str(cabinet.logo))
        w, h = image.getSize()
        logo_height = LOGO_ENTETE
        logo_width = logo_height * w / h
        canvas.drawImage(
            image, MARGIN, top - logo_height, width=logo_width, height=logo_height, mask="auto"
        )
        x = MARGIN + logo_width + 4 * mm
    y = top - 6 * mm

    canvas.setFillColor(color("title"))
    canvas.setFont(SERIF_GRAS, 19)
    canvas.drawString(x, y, signature(context, cabinet))
    y -= 5.2 * mm
    canvas.setFillColor(color("body"))
    canvas.setFont(SERIF, 10)
    for line in cabinet.qualification_lines():
        canvas.drawString(x, y, line)
        y -= 4.2 * mm

    # Coordonnées sous les titres : RPPS, puis le cabinet et son adresse, puis courriel
    # et téléphone — trois lignes au plus, un champ vide ne laisse pas de trou.
    y -= 1.5 * mm
    if cabinet.legal:
        canvas.setFont(SERIF_GRAS, 8.5)
        canvas.setFillColor(color("body"))
        legal = cabinet.legal if ":" in cabinet.legal else f"RPPS : {cabinet.legal}"
        canvas.drawString(x, y, legal)
        y -= 3.9 * mm
    canvas.setFont(SERIF, 8.5)
    canvas.setFillColor(color("title"))
    nom = cabinet.name if cabinet.name != "Cabinet" else ""
    for parts in ((nom, cabinet.address), (cabinet.email, cabinet.phone)):
        line = " · ".join(part for part in parts if part)
        if line:
            canvas.drawString(x, y, line)
            y -= 3.9 * mm
    right = top - logo_height
    y = min(y, right) - 12 * mm
    canvas.setFillColor(color("title"))
    canvas.setFont(SERIF_GRAS, 25)
    heading = layout.title
    if layout.title == "Votre consultation":
        heading = f"Votre consultation du {french_date(context.encounter_date)}"
    canvas.drawString(MARGIN, y, heading)
    y -= 5 * mm

    rows = patient_rows(context, layout)
    row_height = 6 * mm
    block_height = row_height * len(rows) + 2 * mm
    canvas.setFillColor(color("block"))
    canvas.rect(MARGIN, y - block_height, width - 2 * MARGIN, block_height, stroke=0, fill=1)
    ry = y - row_height + 0.6 * mm
    for label, value in rows:
        canvas.setFont(SERIF, 7.5)
        canvas.setFillColor(color("muted"))
        canvas.drawString(MARGIN + 2 * mm, ry + 0.4 * mm, label.upper())
        canvas.setFont(SERIF_GRAS, 11)
        canvas.setFillColor(color("body"))
        canvas.drawString(MARGIN + 42 * mm, ry, value)
        ry -= row_height
    y -= block_height + 5 * mm

    canvas.setFont(SERIF_ITALIQUE, 8.5)
    canvas.setFillColor(color("muted") if context.validated_at else color("accent"))
    canvas.drawString(MARGIN, y, f"{notice_for(context)} Version {context.version}.")
    return y - 9 * mm


def draw_running_header(
    canvas: Canvas,
    context: ExportContext,
    layout: Layout,
    cabinet: Cabinet,
    top: float,
) -> float:
    """Haut des pages suivantes : qui, pour qui, quel document."""
    canvas.setFont(SERIF_GRAS, 12)
    canvas.setFillColor(color("title"))
    canvas.drawString(MARGIN, top, signature(context, cabinet))
    canvas.setFont(SERIF_GRAS, 10)
    canvas.setFillColor(color("body"))
    canvas.drawString(MARGIN + 52 * mm, top, context.patient)
    canvas.setFont(SERIF, 8.5)
    canvas.setFillColor(color("muted"))
    canvas.drawString(
        MARGIN + 52 * mm,
        top - 4.2 * mm,
        f"{layout.title} · {french_date(context.encounter_date)}",
    )
    return top - 13 * mm


def draw_footer(
    canvas: Canvas, layout: Layout, cabinet: Cabinet, width: float, page: int, total: int
) -> None:
    canvas.setFont(SERIF, 8)
    canvas.setFillColor(color("muted"))
    canvas.drawRightString(width - MARGIN, MARGIN / 2, FOOTER.format(page=page, total=total))
    if layout.footer_note and page == total:
        canvas.drawCentredString(width / 2, MARGIN / 2 + 4.5 * mm, layout.footer_note)


def render_pdf(context: ExportContext, cabinet: Cabinet | None = None) -> bytes:
    """PDF A4 dans la mise en page des modèles du praticien."""
    cabinet = cabinet or Cabinet.load()
    layout = layout_for(context.document_type)
    if layout.letter and layout.closing:
        # La signature d'un courrier est celle du praticien, titre compris.
        context = replace(context, practitioner=signature(context, cabinet))
    buffer = io.BytesIO()
    canvas = Canvas(buffer, pagesize=A4)
    canvas.setTitle(layout.title)
    canvas.setAuthor(context.practitioner)
    width, height = A4
    usable = width - 2 * MARGIN

    blocks = body_blocks(context, layout, usable)
    # La place réelle sous l'en-tête : on le pose sur une page d'essai et on mesure,
    # plutôt que d'estimer (une estimation laissait un tiers de page vide).
    essai = Canvas(io.BytesIO(), pagesize=A4)
    first_page_top = draw_letterhead(essai, context, layout, cabinet, width, height - MARGIN)
    other_pages_top = draw_running_header(essai, context, layout, cabinet, height - MARGIN)
    bottom = MARGIN + 2 * mm

    pages: list[list[Block]] = [[]]
    room = first_page_top - bottom
    used = 0.0
    for style, line in blocks:
        step = step_for(style, layout)
        # Un intitulé ne reste jamais seul en bas de page.
        needed = step + (layout.leading * 2 if style == "heading" else 0)
        if used + needed > room:
            pages.append([])
            room = other_pages_top - bottom
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
            y = draw_running_header(canvas, context, layout, cabinet, y)
        for style, line in page:
            if style == "space":
                y -= layout.leading / 2
                continue
            if style == "heading":
                y -= 2.5 * mm
                canvas.setFont(SERIF, layout.heading_size + 3)
                canvas.setFillColor(color("heading"))
                canvas.drawString(MARGIN, y, line)
                canvas.setStrokeColor(color("rule"))
                canvas.setLineWidth(0.6)
                canvas.line(MARGIN, y - 1.6 * mm, width - MARGIN, y - 1.6 * mm)
                y -= layout.leading + 1.5 * mm
                continue
            if style == "muted":
                canvas.setFont(SERIF_ITALIQUE, 10.5)
                canvas.setFillColor(color("muted"))
            else:
                canvas.setFont(SERIF, layout.body_size + 0.5)
                canvas.setFillColor(color("body"))
            canvas.drawString(MARGIN, y, line)
            y -= layout.leading
        draw_footer(canvas, layout, cabinet, width, number, total)
        canvas.showPage()
    if context.figures:
        draw_figures(canvas, context, layout, cabinet, width, height, total)
    canvas.save()
    return buffer.getvalue()


FIGURE_GAP = 6 * mm
CAPTION_HEIGHT = 7 * mm


def draw_figure(
    canvas: Canvas, contenu: bytes, x: float, top: float, max_w: float, max_h: float
) -> float:
    """Pose une photo sans la déformer ; renvoie la hauteur réellement occupée."""
    image = ImageReader(io.BytesIO(contenu))
    w, h = image.getSize()
    scale = min(max_w / w, max_h / h)
    drawn_w, drawn_h = w * scale, h * scale
    canvas.drawImage(image, x, top - drawn_h, width=drawn_w, height=drawn_h)
    return drawn_h


def draw_caption(canvas: Canvas, number: int, legende: str, x: float, y: float, w: float) -> None:
    canvas.setFont(SERIF, 9)
    canvas.setFillColor(color("muted"))
    texte = f"Fig. {number}" + (f" — {legende}" if legende else "")
    canvas.drawString(x, y, wrap(texte, SERIF, 9, w)[0])


def draw_figures(
    canvas: Canvas,
    context: ExportContext,
    layout: Layout,
    cabinet: Cabinet,
    width: float,
    height: float,
    pages_before: int,
) -> None:
    """« Documentation clinique » : toujours sur une nouvelle page, et en dernier.

    La première photo en grand, les suivantes deux par ligne, chacune légendée. Rien de
    clinique ne vient après (règle des modèles du praticien).
    """
    usable = width - 2 * MARGIN
    bottom = MARGIN + 6 * mm
    page = pages_before + 1

    def nouvelle_page(titre: bool) -> float:
        y = draw_running_header(canvas, context, layout, cabinet, height - MARGIN)
        if titre:
            canvas.setFillColor(color("title"))
            canvas.setFont(SERIF_GRAS, 25)
            canvas.drawString(MARGIN, y - 4 * mm, "Documentation clinique")
            y -= 14 * mm
        return y

    y = nouvelle_page(titre=True)
    for index, figure in enumerate(context.figures, start=1):
        if index == 1:
            max_h = min(115 * mm, y - bottom - CAPTION_HEIGHT)
            drawn = draw_figure(canvas, figure.contenu, MARGIN, y, usable, max_h)
            draw_caption(canvas, 1, figure.legende, MARGIN, y - drawn - 4.5 * mm, usable)
            y -= drawn + CAPTION_HEIGHT + FIGURE_GAP
            continue
        colonne = (index - 2) % 2
        demi = (usable - FIGURE_GAP) / 2
        max_h = 72 * mm
        if colonne == 0 and y - max_h - CAPTION_HEIGHT < bottom:
            draw_footer(canvas, layout, cabinet, width, page, page)
            canvas.showPage()
            page += 1
            y = nouvelle_page(titre=False)
        x = MARGIN + colonne * (demi + FIGURE_GAP)
        drawn = draw_figure(canvas, figure.contenu, x, y, demi, max_h)
        draw_caption(canvas, index, figure.legende, x, y - drawn - 4.5 * mm, demi)
        if colonne == 1 or index == len(context.figures):
            y -= max_h + CAPTION_HEIGHT + FIGURE_GAP
    draw_footer(canvas, layout, cabinet, width, page, page)
    canvas.showPage()


def step_for(style: str, layout: Layout) -> float:
    """Hauteur occupée par une ligne, pour paginer exactement comme on dessine."""
    if style == "space":
        return layout.leading / 2
    if style == "heading":
        return layout.leading + 4 * mm
    return layout.leading
