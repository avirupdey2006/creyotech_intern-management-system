from app.services.storage_backend import storage_backend_service
import io
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional
from xml.sax.saxutils import escape

import aiofiles
from pypdf import PdfReader, PdfWriter, Transformation
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import simpleSplit
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    HRFlowable,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import BACKEND_DIR, settings
from app.core.encryption import crypto_engine
from app.core.logging import pino_logger
from app.models.document import Document
from app.models.enums import DocumentType
from app.models.intern_profile import InternProfile

TEMPLATES_DIR = BACKEND_DIR / "app" / "templates"
PDF_BG_DIR = TEMPLATES_DIR / "pdf_backgrounds"

VERIFY_BASE_URL = str(getattr(settings, "frontend_base_url", "http://localhost:3000")).rstrip("/")

# =============================================================================
# LAYOUT CONSTANTS  (measured from HR's real template PDFs)
# Everything is a FRACTION of the background PDF's page size (0.0 - 1.0), so the
# layout adapts to whatever page size HR's template uses. If a template ever
# needs a nudge, change the numbers here - nothing else.
# x fractions are measured from the LEFT edge, y fractions from the TOP edge
# unless the name says "from bottom".
# =============================================================================

# ---- Offer letters (portrait letterhead) ------------------------------------
# The letterhead already has a printed sign-off ("Regards / Priya Iyer / HR Team")
# at bottom-left, so the letter text stops above it and the verification box sits
# to the RIGHT of that sign-off, above the purple footer.
LETTER_SIDE_MARGIN = 0.06      # left/right text margin
LETTER_TEXT_TOP = 0.108        # text starts just below the header/logo (header ends at ~0.094)
LETTER_TEXT_TOP_NO_BG = 0.16   # only used when no background PDF exists (own banner is drawn)
LETTER_TEXT_BOTTOM = 0.826     # text must end above the printed sign-off (starts at ~0.836)
LETTER_BOX_LEFT = 0.375        # verification box: right of the printed sign-off text
LETTER_BOX_RIGHT = 0.945
LETTER_BOX_TOP = 0.835         # (y from top)
LETTER_BOX_BOTTOM = 0.900      # (y from top) stays above the footer tab (starts at ~0.907)

# ---- Completion certificate (landscape template) ----------------------------
CERT_BODY_LEFT = 0.18          # aligned with the big "CERTIFICATE" title
CERT_BODY_RIGHT = 0.575        # stays left of the seal (starts at ~0.60)
CERT_BODY_TOP = 0.385          # below the printed "OF INTERNSHIP" line (ends at ~0.35)
CERT_BODY_BOTTOM = 0.83        # above the verification box
CERT_ISSUE_DATE_POS = (0.778, 0.0625)  # (x, baseline y_top) on the printed "Issue Date: ____" line
CERT_NUMBER_POS = (0.808, 0.099)       # (x, baseline y_top) on the printed "Certificate No: ____" line
CERT_STAMP_MAX_WIDTH = 0.165           # max text width of those two fields (fraction of page width)
CERT_BOX_LEFT = 0.18
CERT_BOX_RIGHT = 0.55          # stays left of the printed signature line (starts at ~0.566)
CERT_BOX_BOTTOM = 0.058        # (fraction of page height, from bottom) above the orange wave
CERT_BOX_HEIGHT = 18 * mm


def _resolve_background_pdf(document_type: str) -> Optional[Path]:
    """
    Locates the appropriate HR background PDF template in app/templates/pdf_backgrounds/.
    Notice: Provisional Offer and Final Offer can share offer_letter_bg.pdf or use specific filenames.
    """
    if document_type == DocumentType.COMPLETION_CERTIFICATE.value:
        candidates = [
            PDF_BG_DIR / "completion_certificate_bg.pdf",
            PDF_BG_DIR / "certificate_bg.pdf",
            PDF_BG_DIR / "certificate.pdf",
        ]
    elif document_type == DocumentType.PROVISIONAL_OFFER.value:
        candidates = [
            PDF_BG_DIR / "provisional_offer_bg.pdf",
            PDF_BG_DIR / "offer_letter_bg.pdf",
            PDF_BG_DIR / "offer_template.pdf",
        ]
    else:
        candidates = [
            PDF_BG_DIR / "final_offer_bg.pdf",
            PDF_BG_DIR / "provisional_offer_bg.pdf",
            PDF_BG_DIR / "offer_letter_bg.pdf",
            PDF_BG_DIR / "offer_template.pdf",
        ]
    for path in candidates:
        if path.exists():
            return path
    return None


def _format_duration_label(start_date, end_date) -> str:
    days = (end_date - start_date).days
    months = max(1, round(days / 30))
    return f"{months} {'Month' if months == 1 else 'Months'}"


# -----------------------------------------------------------------------------
# Page geometry helpers
# -----------------------------------------------------------------------------
def _page_size(bg_path: Optional[Path], is_cert: bool) -> tuple[float, float]:
    """Use the HR template's own page size so nothing is ever scaled or shifted."""
    if bg_path is not None:
        page = PdfReader(str(bg_path)).pages[0]
        w = float(page.mediabox.width)
        h = float(page.mediabox.height)
        rotation = int(page.get("/Rotate", 0) or 0) % 180
        return (h, w) if rotation == 90 else (w, h)
    return landscape(A4) if is_cert else A4


def _frame_geometry(is_cert: bool, has_bg: bool, pw: float, ph: float) -> tuple[float, float, float, float]:
    """Returns (x, y_bottom, width, height) of the text frame in PDF points."""
    if is_cert:
        left = CERT_BODY_LEFT if has_bg else 0.12
        right = CERT_BODY_RIGHT if has_bg else 0.88
        top = ph * (1 - CERT_BODY_TOP)
        bottom = ph * (1 - CERT_BODY_BOTTOM)
        return left * pw, bottom, (right - left) * pw, top - bottom

    side = LETTER_SIDE_MARGIN * pw
    top = ph * (1 - (LETTER_TEXT_TOP if has_bg else LETTER_TEXT_TOP_NO_BG))
    bottom = ph * (1 - LETTER_TEXT_BOTTOM)
    return side, bottom, pw - 2 * side, top - bottom


# -----------------------------------------------------------------------------
# Verification box (QR code + 12-char alphanumeric code)
# -----------------------------------------------------------------------------
def _draw_verification_box(
    c: canvas.Canvas,
    ctx: dict,
    x: float,
    y: float,
    w: float,
    h: float,
    *,
    show_reference: bool,
) -> None:
    c.saveState()
    c.setFillColor(colors.HexColor("#F8FAFC"))
    c.setStrokeColor(colors.HexColor("#CBD5E1"))
    c.setLineWidth(0.6)
    c.roundRect(x, y, w, h, 2 * mm, fill=1, stroke=1)

    pad = 2 * mm
    qr_size = h - 2 * pad
    verify_url = f"{VERIFY_BASE_URL}/verify?code={ctx['verification_code']}"
    qr_widget = qr.QrCodeWidget(verify_url)
    b = qr_widget.getBounds()
    qw, qh = b[2] - b[0], b[3] - b[1]
    d = Drawing(qr_size, qr_size, transform=[qr_size / qw, 0, 0, qr_size / qh, 0, 0])
    d.add(qr_widget)
    d.drawOn(c, x + pad, y + pad)

    tx = x + pad + qr_size + 4 * mm
    text_w = x + w - pad - tx

    lines: list[tuple[str, float, colors.Color, str]] = [
        ("Helvetica-Bold", 8.8, colors.HexColor("#0F172A"), f"VERIFICATION CODE: {ctx['verification_code']}")
    ]
    if show_reference:
        ref_line = f"Ref. No.: {ctx['reference_id']}   |   Issue Date: {ctx['issue_date']}"
        for part in simpleSplit(ref_line, "Helvetica", 7.6, text_w):
            lines.append(("Helvetica", 7.6, colors.HexColor("#334155"), part))
    note = f"Scan the QR code or enter the code at {VERIFY_BASE_URL}/verify to validate this document."
    for part in simpleSplit(note, "Helvetica", 7, text_w):
        lines.append(("Helvetica", 7, colors.HexColor("#475569"), part))

    total = sum(size * 1.38 for _, size, _, _ in lines)
    cursor = y + h / 2 + total / 2
    for font, size, color, text in lines:
        lead = size * 1.38
        cursor -= lead
        c.setFont(font, size)
        c.setFillColor(color)
        c.drawString(tx, cursor + lead * 0.26, text)
    c.restoreState()


def _draw_fit_text(c: canvas.Canvas, text: str, x: float, y: float, max_w: float, font: str, size: float) -> None:
    """Draws text on a template field, shrinking it so it never runs past the field."""
    while size > 6 and stringWidth(text, font, size) > max_w:
        size -= 0.25
    c.setFont(font, size)
    c.drawString(x, y, text)


# -----------------------------------------------------------------------------
# Per-page chrome (stamps + verification box). Runs on EVERY page.
# -----------------------------------------------------------------------------
def _make_page_callback(
    document_type: str, ctx: dict, has_bg: bool, pw: float, ph: float
) -> Callable:
    is_cert = document_type == DocumentType.COMPLETION_CERTIFICATE.value

    def _letter_chrome(c: canvas.Canvas) -> None:
        if not has_bg:
            c.setStrokeColor(colors.HexColor("#0F172A"))
            c.setLineWidth(0.8)
            c.rect(12 * mm, 12 * mm, pw - 24 * mm, ph - 24 * mm)
            c.setFillColor(colors.HexColor("#0F172A"))
            c.rect(12 * mm, ph - 36 * mm, pw - 24 * mm, 24 * mm, fill=1, stroke=0)
            c.setFillColor(colors.white)
            c.setFont("Helvetica-Bold", 15)
            c.drawString(20 * mm, ph - 23 * mm, "CREYOTECH")
            c.setFillColor(colors.HexColor("#93C5FD"))
            c.setFont("Helvetica", 8.5)
            c.drawString(20 * mm, ph - 29 * mm, "CREYOTECH IT Services  |  Technology & Consulting")

        if not has_bg:
            # Mirror the printed sign-off of HR's letterhead so the no-template fallback looks the same.
            c.setFillColor(colors.HexColor("#1E293B"))
            c.setFont("Helvetica", 9)
            c.drawString(0.023 * pw, ph * (1 - 0.848), "Regards,")
            c.drawString(0.023 * pw, ph * (1 - 0.915), "HR Team, Creyotech IT Services")

        _draw_verification_box(
            c,
            ctx,
            LETTER_BOX_LEFT * pw,
            ph * (1 - LETTER_BOX_BOTTOM),
            (LETTER_BOX_RIGHT - LETTER_BOX_LEFT) * pw,
            ph * (LETTER_BOX_BOTTOM - LETTER_BOX_TOP),
            show_reference=True,
        )

    def _cert_chrome(c: canvas.Canvas) -> None:
        if has_bg:
            # Fill the blank "Issue Date: ____" and "Certificate No.: ____" lines of HR's template.
            c.setFillColor(colors.HexColor("#0F172A"))
            max_w = CERT_STAMP_MAX_WIDTH * pw
            _draw_fit_text(
                c, ctx["issue_date"], CERT_ISSUE_DATE_POS[0] * pw, ph * (1 - CERT_ISSUE_DATE_POS[1]),
                max_w, "Helvetica-Bold", 10,
            )
            _draw_fit_text(
                c, ctx["reference_id"], CERT_NUMBER_POS[0] * pw, ph * (1 - CERT_NUMBER_POS[1]),
                max_w, "Helvetica-Bold", 10,
            )
            box_x = CERT_BOX_LEFT * pw
            box_w = (CERT_BOX_RIGHT - CERT_BOX_LEFT) * pw
        else:
            c.setStrokeColor(colors.HexColor("#0F172A"))
            c.setLineWidth(1.4)
            c.rect(12 * mm, 12 * mm, pw - 24 * mm, ph - 24 * mm)
            c.setStrokeColor(colors.HexColor("#B45309"))
            c.setLineWidth(0.6)
            c.rect(14 * mm, 14 * mm, pw - 28 * mm, ph - 28 * mm)
            c.setFillColor(colors.HexColor("#0F172A"))
            c.setFont("Helvetica-Bold", 28)
            c.drawCentredString(pw / 2, ph * (1 - 0.24), "CERTIFICATE")
            c.setFont("Helvetica-Bold", 14)
            c.drawCentredString(pw / 2, ph * (1 - 0.31), "OF INTERNSHIP")
            c.setFont("Helvetica", 9)
            c.drawRightString(
                pw - 20 * mm, ph * (1 - 0.09),
                f"Issue Date: {ctx['issue_date']}     Certificate No.: {ctx['reference_id']}",
            )
            box_x = 0.12 * pw
            box_w = 0.76 * pw

        _draw_verification_box(
            c, ctx, box_x, CERT_BOX_BOTTOM * ph, box_w, CERT_BOX_HEIGHT, show_reference=False
        )

    def _callback(c: canvas.Canvas, _doc) -> None:
        c.saveState()
        (_cert_chrome if is_cert else _letter_chrome)(c)
        c.restoreState()

    return _callback


# -----------------------------------------------------------------------------
# Story builders
# -----------------------------------------------------------------------------
def _letter_styles(base: float, s: float) -> dict:
    fs = base * s
    lead = fs * 1.34
    ink = colors.HexColor("#1E293B")
    dark = colors.HexColor("#0F172A")
    body = ParagraphStyle(
        "LBody", fontName="Helvetica", fontSize=fs, leading=lead,
        alignment=TA_JUSTIFY, textColor=ink, spaceAfter=fs * 0.45,
    )
    return {
        "title": ParagraphStyle(
            "LTitle", fontName="Helvetica-Bold", fontSize=fs + 3.2, leading=(fs + 3.2) * 1.25,
            alignment=TA_CENTER, textColor=dark, spaceAfter=fs * 0.4,
        ),
        "meta": ParagraphStyle(
            "LMeta", fontName="Helvetica", fontSize=fs, leading=lead, alignment=TA_LEFT, textColor=ink,
        ),
        "meta_right": ParagraphStyle(
            "LMetaRight", fontName="Helvetica", fontSize=fs, leading=lead, alignment=TA_RIGHT, textColor=ink,
        ),
        "subj": ParagraphStyle(
            "LSubj", fontName="Helvetica-Bold", fontSize=fs + 0.4, leading=lead,
            textColor=dark, spaceBefore=fs * 0.45, spaceAfter=fs * 0.45,
        ),
        "sec": ParagraphStyle(
            "LSec", fontName="Helvetica-Bold", fontSize=fs + 0.4, leading=lead,
            textColor=dark, spaceBefore=fs * 0.6, spaceAfter=fs * 0.25, keepWithNext=1,
        ),
        "body": body,
        "bullet": ParagraphStyle(
            "LBullet", parent=body, alignment=TA_LEFT, leftIndent=12, bulletIndent=2,
            bulletFontName="Helvetica", bulletFontSize=fs, spaceAfter=fs * 0.15,
        ),
    }


_ZERO_PAD_TABLE = [
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("LEFTPADDING", (0, 0), (-1, -1), 0),
    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ("TOPPADDING", (0, 0), (-1, -1), 0),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
]


def _bullets(items: list[str], style: ParagraphStyle) -> list:
    return [Paragraph(text, style, bulletText="•") for text in items]


def _two_col_bullets(items: list[str], style: ParagraphStyle, width: float) -> Table:
    """Compact two-column bullet grid (keeps every item and its wording, saves vertical space)."""
    rows = []
    for i in range(0, len(items), 2):
        row = [Paragraph(t, style, bulletText="•") for t in items[i : i + 2]]
        if len(row) < 2:
            row.append("")
        rows.append(row)
    table = Table(rows, colWidths=[width * 0.5, width * 0.5])
    table.setStyle(TableStyle(_ZERO_PAD_TABLE))
    return table


def _address_and_reference_block(ctx: dict, st: dict, width: float) -> Table:
    """Recipient address on the left, Date + Reference No. on the right - one compact row."""
    left = Paragraph(
        f"<b>To,</b><br/><b>{ctx['full_name']}</b><br/>{ctx['address']}<br/>"
        f"{ctx['city']}, {ctx['state']} – {ctx['pin_code']}",
        st["meta"],
    )
    right = Paragraph(
        f"<b>Date:</b> {ctx['issue_date']}<br/><b>Reference No.:</b> {ctx['reference_id']}",
        st["meta_right"],
    )
    table = Table([[left, right]], colWidths=[width * 0.56, width * 0.44])
    table.setStyle(TableStyle(_ZERO_PAD_TABLE))
    return table


def _role_clean(ctx: dict) -> str:
    return ctx["internship_role"].removesuffix(" Intern").removesuffix(" intern").strip()


# NOTE: The closing "Regards / Priya Iyer / HR Team" sign-off is PRINTED on HR's letterhead
# template, so the letter bodies below intentionally do not add their own sign-off block.
def _build_provisional_offer_story(ctx: dict, s: float, width: float) -> list:
    st = _letter_styles(10.0, s)
    role = _role_clean(ctx)
    return [
        Paragraph("PROVISIONAL INTERNSHIP OFFER LETTER", st["title"]),
        HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#CBD5E1")),
        Spacer(1, 6),
        _address_and_reference_block(ctx, st, width),
        Paragraph(f"Subject: Provisional Offer for the Position of {role} Intern", st["subj"]),
        Paragraph(f"Dear <b>{ctx['full_name']}</b>,", st["body"]),
        Paragraph(
            f"We are pleased to offer you a provisional internship opportunity at <b>CREYOTECH (CREYOTECH IT Services)</b> "
            f"for the position of <b>{role} Intern</b>, subject to the terms and conditions outlined below.",
            st["body"],
        ),
        Paragraph("1. Evaluation Period", st["sec"]),
        *_bullets(
            [
                f"<b>Start Date:</b> {ctx['start_date_formatted']}",
                f"<b>Duration:</b> {ctx['duration_display']}",
                f"<b>Work Mode:</b> {ctx['work_mode']}",
                f"<b>Work Schedule:</b> {ctx['work_schedule']}",
            ],
            st["bullet"],
        ),
        Spacer(1, 3),
        Paragraph(
            "During this period, you will be assigned a project designed to assess your technical capabilities, "
            "problem-solving skills, quality of work, learning ability, and overall suitability for the role.",
            st["body"],
        ),
        Paragraph("2. Nature of the Provisional Engagement", st["sec"]),
        Paragraph(
            "This phase is strictly for evaluation purposes and does not constitute a confirmation of the internship "
            "appointment. Upon successful completion of the evaluation period, and subject to satisfactory performance "
            "and review by the concerned team, you may be issued a Final Internship Offer Letter confirming your "
            "internship tenure and applicable terms.",
            st["body"],
        ),
        Paragraph("3. Stipend", st["sec"]),
        Paragraph(
            "Any stipend, if applicable, will be determined based on your performance during the evaluation phase and "
            "communicated by the company through the appropriate official communication.",
            st["body"],
        ),
        Paragraph("4. General Expectations", st["sec"]),
        Paragraph(
            "You are expected to demonstrate professionalism, discipline, timely communication, responsible project "
            "execution, and adherence to the company's policies and confidentiality requirements throughout the "
            "evaluation period.",
            st["body"],
        ),
        Paragraph(
            "We look forward to evaluating your capabilities and providing you with an opportunity to demonstrate your "
            "potential. We wish you a productive and valuable learning experience with <b>CREYOTECH</b>.",
            st["body"],
        ),
    ]


def _build_final_offer_story(ctx: dict, s: float, width: float) -> list:
    st = _letter_styles(9.2, s)
    role = _role_clean(ctx)
    return [
        Paragraph("FINAL INTERNSHIP OFFER LETTER", st["title"]),
        HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#CBD5E1")),
        Spacer(1, 4),
        _address_and_reference_block(ctx, st, width),
        Paragraph(f"Subject: Final Offer of Internship — {role}", st["subj"]),
        Paragraph(f"Dear <b>{ctx['full_name']}</b>,", st["body"]),
        Paragraph(
            f"Following the successful completion of your evaluation period, we are pleased to formally offer you the "
            f"position of <b>{role} Intern</b> at <b>CREYOTECH (CREYOTECH IT Services)</b>. Your internship will "
            f"commence on <b>{ctx['start_date_formatted']}</b> and continue for a duration of "
            f"<b>{ctx['duration_display']}</b>, subject to the following terms and conditions.",
            st["body"],
        ),
        Paragraph("1. Appointment Details", st["sec"]),
        _two_col_bullets(
            [
                f"<b>Designation:</b> {role} Intern",
                f"<b>Work Mode:</b> {ctx['work_mode']}",
                f"<b>Duration:</b> {ctx['duration_display']} (Starting {ctx['start_date_formatted']})",
                f"<b>Work Schedule:</b> {ctx['work_schedule']}",
                f"<b>Reporting Manager:</b> {ctx['reporting_manager']}",
                "<b>Stipend:</b> Details will be shared separately by the company.",
            ],
            st["bullet"],
            width,
        ),
        Paragraph("2. Key Responsibilities", st["sec"]),
        *_bullets(
            [
                "Develop, implement, test, and maintain solutions relevant to your assigned project.",
                "Apply technical knowledge and problem-solving skills to project requirements.",
                "Follow coding standards, documentation practices, and quality guidelines.",
                "Collaborate with team members and incorporate feedback to improve deliverables.",
                "Provide regular progress updates and complete assigned tasks within agreed timelines.",
            ],
            st["bullet"],
        ),
        Paragraph("3. Internship Completion and Certificate", st["sec"]),
        Paragraph(
            "An Internship Completion Certificate may be awarded upon successful completion of the prescribed internship "
            "tenure, satisfactory performance, and fulfilment of the company's completion requirements. The certificate "
            "will be issued following the company's verification and approval process.",
            st["body"],
        ),
        Paragraph("4. Cessation and Termination", st["sec"]),
        Paragraph(
            "The intern may resign from the internship by providing 15 days' prior notice. The company may terminate "
            "the internship by providing 7 days' notice, or immediately in cases involving serious misconduct, policy "
            "violations, unethical practices, misrepresentation, or unsatisfactory performance, subject to applicable "
            "company policies and law.",
            st["body"],
        ),
        Paragraph("5. General Terms", st["sec"]),
        *_bullets(
            [
                "Professional conduct, discipline, confidentiality, and timely communication are expected throughout the internship.",
                "Tasks, reporting arrangements, and work schedules may be adjusted according to operational requirements.",
                "Company information, credentials, project materials, and confidential data must not be disclosed or misused.",
                "This internship does not guarantee permanent employment or full-time conversion.",
                "Any applicable stipend and payment terms will be governed by the details communicated in this offer and the company's applicable policies.",
            ],
            st["bullet"],
        ),
        Spacer(1, 3),
        Paragraph(
            "We welcome you to <b>CREYOTECH</b> and look forward to your contribution, professional growth, and "
            "successful completion of the internship. We wish you a rewarding and productive experience with our team.",
            st["body"],
        ),
        Paragraph(
            "Please confirm your acceptance of this offer through the company's designated acceptance process.",
            st["body"],
        ),
    ]


def _build_completion_certificate_story(ctx: dict, s: float, width: float, has_bg: bool) -> list:
    """
    Certificate body only: HR's template already carries the logo, title, seal, signature and
    the Issue Date / Certificate No. fields, so nothing here may collide with those.
    """
    align = TA_LEFT if has_bg else TA_CENTER
    ink = colors.HexColor("#1E293B")

    lead_style = ParagraphStyle(
        "CertLead", fontName="Helvetica", fontSize=13 * s, leading=18 * s,
        alignment=align, textColor=colors.HexColor("#334155"), spaceAfter=4 * s,
    )

    name_size = 28 * s
    while name_size > 12 and stringWidth(ctx["full_name_raw"], "Helvetica-Bold", name_size) > width:
        name_size -= 1
    name_style = ParagraphStyle(
        "CertName", fontName="Helvetica-Bold", fontSize=name_size, leading=name_size * 1.25,
        alignment=align, textColor=colors.HexColor("#1D4ED8"), spaceAfter=10 * s,
    )
    body_style = ParagraphStyle(
        "CertBody", fontName="Helvetica", fontSize=12 * s, leading=18 * s,
        alignment=align, textColor=ink, spaceAfter=8 * s,
    )

    return [
        Paragraph("This is to certify that", lead_style),
        Paragraph(ctx["full_name"], name_style),
        Paragraph(
            f"of <b>{ctx['college_name']}</b> has successfully completed an internship at "
            f"<b>CREYOTECH</b> as a <b>{ctx['internship_role']}</b> from "
            f"<b>{ctx['start_date_formatted']}</b> to <b>{ctx['end_date_formatted']}</b>, "
            f"spanning <b>{ctx['duration_display']}</b>.",
            body_style,
        ),
        Paragraph(
            "During the internship, the intern demonstrated commitment to assigned responsibilities, "
            "professional conduct, and a willingness to learn and contribute to the organization.",
            body_style,
        ),
        Paragraph(
            "We appreciate their efforts and wish them continued success in their academic and professional journey.",
            body_style,
        ),
    ]


def _story_height(story: list, width: float) -> float:
    total = 0.0
    for flowable in story:
        _, h = flowable.wrap(width, 100000)
        total += h + flowable.getSpaceBefore() + flowable.getSpaceAfter()
    return total


def _fit_story(build: Callable[[float], list], width: float, height: float, scales: list[float]) -> list:
    """
    Largest font scale (scales are listed biggest -> smallest) whose story fits the frame, which
    guarantees a single page. If even the smallest scale does not fit (extremely long inputs),
    the smallest scale is used so the text is as compact as it can possibly be.
    """
    for s in scales:
        story = build(s)
        if _story_height(story, width) <= height - 2:
            return story
    return build(scales[-1])


# -----------------------------------------------------------------------------
# Rendering
# -----------------------------------------------------------------------------
def _merge_with_background(foreground_bytes: bytes, bg_path: Path) -> bytes:
    """
    Puts HR's letterhead/certificate template behind EVERY generated page.
    Some template PDFs (including HR's letterheads) have a non-zero page origin, e.g.
    MediaBox [0 7.83 595.5 850.08]; the generated content is shifted by that origin so it
    lands exactly where it was designed to on the template.
    """
    fg_reader = PdfReader(io.BytesIO(foreground_bytes))
    writer = PdfWriter()
    for fg_page in fg_reader.pages:
        base_page = PdfReader(str(bg_path)).pages[0]
        origin_x = float(base_page.mediabox.left)
        origin_y = float(base_page.mediabox.bottom)
        base_page.merge_transformed_page(
            fg_page, Transformation().translate(tx=origin_x, ty=origin_y)
        )
        writer.add_page(base_page)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def _render_pdf_bytes_from_template(
    document_type: str,
    context: dict,
) -> bytes:
    """
    Renders the CREYOTECH Provisional Offer Letter, Final Offer Letter, or Completion Certificate
    and overlays onto HR's PDF template in app/templates/pdf_backgrounds/ if present.
    """
    # Normalize context defaults so both direct unit tests and full ORM calls work seamlessly
    issue_date = context.get("issue_date") or context.get("generated_date") or "26 October, 2026"
    start_raw = str(context.get("start_date", "2026-11-01"))
    end_raw = str(context.get("end_date", "2027-04-30"))

    try:
        start_fmt = datetime.fromisoformat(start_raw).strftime("%d %B, %Y")
    except ValueError:
        start_fmt = start_raw

    try:
        end_fmt = datetime.fromisoformat(end_raw).strftime("%d %B, %Y")
    except ValueError:
        end_fmt = end_raw

    normalized_ctx = {
        "issue_date": issue_date,
        "generated_date": issue_date,
        "reference_id": context.get("reference_id", "CT/IMS/2026/0001"),
        "verification_code": context.get("verification_code", "CTMUWS67PSNS"),
        "full_name": context.get("full_name", "Candidate Name"),
        "college_name": context.get("college_name", "University"),
        "internship_role": context.get("internship_role", "Software Engineer"),
        "start_date": start_raw,
        "end_date": end_raw,
        "start_date_formatted": context.get("start_date_formatted") or start_fmt,
        "end_date_formatted": context.get("end_date_formatted") or end_fmt,
        "duration_display": context.get("duration_display", "6 Months"),
        "address": context.get("address") or "Sector V, Salt Lake",
        "city": context.get("city") or "Kolkata",
        "state": context.get("state") or "West Bengal",
        "pin_code": context.get("pin_code") or "700091",
        "work_mode": context.get("work_mode") or "Remote",
        "work_schedule": context.get("work_schedule") or "Monday to Friday (10:00 AM - 6:00 PM IST)",
        "reporting_manager": context.get("reporting_manager") or "Technical Project Manager, CREYOTECH",
        "issuer_remarks": context.get("issuer_remarks") or "",
    }

    # XML-escaped copy for Paragraph text (names like "A & B College" must not break the PDF)
    safe_ctx = {k: (escape(v) if isinstance(v, str) else v) for k, v in normalized_ctx.items()}
    safe_ctx["full_name_raw"] = normalized_ctx["full_name"]

    is_cert = document_type == DocumentType.COMPLETION_CERTIFICATE.value
    bg_pdf_path = _resolve_background_pdf(document_type)
    has_bg = bool(bg_pdf_path and bg_pdf_path.exists())

    pw, ph = _page_size(bg_pdf_path if has_bg else None, is_cert)
    fx, fy, fw, fh = _frame_geometry(is_cert, has_bg, pw, ph)

    letter_scales = [round(1.0 - 0.02 * i, 2) for i in range(0, 20)]   # 1.00 -> 0.62
    cert_scales = [round(1.0 - 0.03 * i, 2) for i in range(0, 15)]     # 1.00 -> 0.58

    if document_type == DocumentType.PROVISIONAL_OFFER.value:
        story = _fit_story(
            lambda s: _build_provisional_offer_story(safe_ctx, s, fw), fw, fh, letter_scales
        )
    elif document_type == DocumentType.FINAL_OFFER.value:
        story = _fit_story(
            lambda s: _build_final_offer_story(safe_ctx, s, fw), fw, fh, letter_scales
        )
    else:
        story = _fit_story(
            lambda s: _build_completion_certificate_story(safe_ctx, s, fw, has_bg), fw, fh, cert_scales
        )

    buffer = io.BytesIO()
    doc = BaseDocTemplate(
        buffer,
        pagesize=(pw, ph),
        title=f"CREYOTECH - {document_type} - {normalized_ctx['verification_code']}",
        author="CREYOTECH IT Services",
    )
    frame = Frame(fx, fy, fw, fh, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0, id="body")
    callback = _make_page_callback(document_type, normalized_ctx, has_bg, pw, ph)
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=callback)])
    doc.build(story)

    foreground_bytes = buffer.getvalue()
    buffer.close()

    if has_bg and bg_pdf_path is not None:
        return _merge_with_background(foreground_bytes, bg_pdf_path)
    return foreground_bytes


class PDFGeneratorService:
    """Idempotent CREYOTECH PDF generator with 12-char verification codes and Fernet encryption."""

    async def generate_and_store_document(
        self,
        db: AsyncSession,
        *,
        profile: InternProfile,
        document_type: str,
        admin_approved_by: uuid.UUID,
        idempotency_key: str,
        issuer_remarks: Optional[str] = None,
    ) -> tuple[Document, bytes, bool]:
        existing_stmt = select(Document).where(
            Document.profile_id == profile.profile_id,
            Document.document_type == document_type,
        )
        existing_doc = (await db.execute(existing_stmt)).scalar_one_or_none()
        if existing_doc:
            if issuer_remarks and existing_doc.issuer_remarks != issuer_remarks:
                existing_doc.issuer_remarks = issuer_remarks
                await db.flush()
            decrypted_bytes = await self.read_decrypted_document(existing_doc)
            pino_logger.info(
                "Idempotent hit: returning existing generated document",
                document_id=str(existing_doc.document_id),
                verification_code=existing_doc.verification_code,
                profile_id=str(profile.profile_id),
                document_type=document_type,
                idempotency_key=idempotency_key,
            )
            return existing_doc, decrypted_bytes, False

        verification_code = crypto_engine.generate_verification_code(12)
        for _ in range(5):
            collision = (
                await db.execute(
                    select(Document).where(Document.verification_code == verification_code)
                )
            ).scalar_one_or_none()
            if not collision:
                break
            verification_code = crypto_engine.generate_verification_code(12)

        now_utc = datetime.now(timezone.utc)
        doc_uuid = uuid.uuid4()
        clean_remarks = (
            issuer_remarks.strip()
            if issuer_remarks and issuer_remarks.strip()
            else "Successfully satisfied all internship evaluation and compliance requirements."
        )

        prefix_map = {
            DocumentType.PROVISIONAL_OFFER.value: "CT/PROV",
            DocumentType.FINAL_OFFER.value: "CT/FINAL",
            DocumentType.COMPLETION_CERTIFICATE.value: "CT/CERT",
        }
        ref_prefix = prefix_map.get(document_type, "CT/IMS")

        context = {
            "issue_date": now_utc.strftime("%d %B, %Y"),
            "generated_date": now_utc.strftime("%d %B, %Y"),
            "reference_id": f"{ref_prefix}/{now_utc.year}/{str(doc_uuid)[:8].upper()}",
            "verification_code": verification_code,
            "full_name": profile.full_name,
            "college_name": profile.college_name,
            "internship_role": profile.internship_role,
            "start_date": profile.start_date.isoformat(),
            "end_date": profile.end_date.isoformat(),
            "start_date_formatted": profile.start_date.strftime("%d %B, %Y"),
            "end_date_formatted": profile.end_date.strftime("%d %B, %Y"),
            "duration_display": _format_duration_label(profile.start_date, profile.end_date),
            "address": profile.address or "Sector V, Salt Lake",
            "city": profile.city or "Kolkata",
            "state": profile.state or "West Bengal",
            "pin_code": profile.pin_code or "700091",
            "work_mode": profile.work_mode or "Remote",
            "work_schedule": profile.work_schedule or "Monday to Friday (10:00 AM - 6:00 PM IST)",
            "reporting_manager": profile.reporting_manager or "Technical Project Manager, CREYOTECH",
            "issuer_remarks": clean_remarks,
        }

        pdf_bytes = _render_pdf_bytes_from_template(document_type, context)
        checksum = crypto_engine.sha256_checksum(pdf_bytes)
        encrypted_bytes = crypto_engine.encrypt_bytes(pdf_bytes)

        filename = f"{profile.profile_id}_{document_type.lower()}_{verification_code}.pdf.enc"
        stored_location = await storage_backend_service.save_encrypted_document(
            filename, encrypted_bytes
        )

        doc_record = Document(
            document_id=doc_uuid,
            profile_id=profile.profile_id,
            document_type=document_type,
            storage_path=stored_location,
            checksum_sha256=checksum,
            verification_code=verification_code,
            issuer_remarks=clean_remarks,
            is_valid=True,
            admin_approved_by=admin_approved_by,
        )
        db.add(doc_record)
        await db.flush()

        pino_logger.info(
            "Generated and encrypted CREYOTECH PDF with 12-char verification code",
            document_id=str(doc_record.document_id),
            verification_code=verification_code,
            profile_id=str(profile.profile_id),
            document_type=document_type,
            checksum_sha256=checksum,
            idempotency_key=idempotency_key,
        )
        return doc_record, pdf_bytes, True

    async def read_decrypted_document(self, document: Document) -> bytes:
        encrypted_bytes = await storage_backend_service.read_encrypted_document(
            document.storage_path
        )
        decrypted_bytes = crypto_engine.decrypt_bytes(encrypted_bytes)
        computed_checksum = crypto_engine.sha256_checksum(decrypted_bytes)
        if computed_checksum != document.checksum_sha256:
            raise ValueError("Document integrity check failed: SHA-256 checksum mismatch.")
        return decrypted_bytes


pdf_generator_service = PDFGeneratorService()