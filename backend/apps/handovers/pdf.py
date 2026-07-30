"""PDF rendering for a handover — a printable record of the transfer."""

import io
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from apps.handovers.models import Handover


def _display(user) -> str:
    if user is None:
        return "—"
    return user.name or user.email


def render_handover_pdf(handover: Handover) -> bytes:
    """Return the handover as a PDF document (bytes)."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=f"Handover — {handover.task.title}",
    )

    styles = getSampleStyleSheet()
    heading = styles["Title"]
    section = ParagraphStyle(
        "Section", parent=styles["Heading2"], spaceBefore=10, spaceAfter=4
    )
    body = ParagraphStyle("Body", parent=styles["BodyText"], leading=15)
    muted = ParagraphStyle(
        "Muted", parent=styles["BodyText"], textColor=colors.HexColor("#666666")
    )

    meta_rows = [
        ["Task", handover.task.title],
        ["Project", handover.task.project.name],
        ["From", _display(handover.from_user)],
        ["To", _display(handover.to_user)],
        ["Status", handover.get_status_display()],
        ["Submitted", handover.created_at.strftime("%Y-%m-%d %H:%M")],
    ]
    if handover.reviewer:
        meta_rows.append(["Reviewed by", _display(handover.reviewer)])
    if handover.reviewed_at:
        meta_rows.append(
            ["Reviewed at", handover.reviewed_at.strftime("%Y-%m-%d %H:%M")]
        )

    meta_table = Table(meta_rows, colWidths=[35 * mm, None])
    meta_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#444444")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LINEBELOW", (0, 0), (-1, -2), 0.25, colors.HexColor("#dddddd")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )

    story = [
        Paragraph("Task handover", heading),
        Paragraph(
            f"Workspace: {escape(handover.workspace.name)}", muted
        ),
        Spacer(1, 8),
        meta_table,
    ]

    def _section(title: str, text: str):
        if not text:
            return
        story.append(Paragraph(title, section))
        for line in text.splitlines():
            story.append(Paragraph(escape(line) or "&nbsp;", body))

    _section("Work summary", handover.summary)
    _section("Pending items", handover.pending_items)
    _section("Resources", handover.resources)
    _section("Review comment", handover.review_comment)

    doc.build(story)
    return buffer.getvalue()
