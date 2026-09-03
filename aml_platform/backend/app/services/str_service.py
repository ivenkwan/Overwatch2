"""
STR compliance helpers (TASK-006): submission validation, status transitions
and the JFIU-style PDF export with content hashing.
"""

import hashlib
import io
from typing import Optional

STR_NARRATIVE_FIELDS = (
    "triggering_factors",
    "subject_background",
    "digital_footprints",
    "transaction_summary",
)

MIN_FIELD_LENGTH = 10

# Allowed filing-status transitions (TASK-006 filing workflow tracking).
STR_STATUS_TRANSITIONS = {
    "draft": {"under_review", "filed", "withdrawn"},
    "under_review": {"filed", "draft", "withdrawn"},
    "filed": set(),
    "withdrawn": set(),
}


def validate_str_submission(record: dict) -> list:
    """Return a list of mandatory-field problems (empty list == valid)."""
    problems = []
    for field in STR_NARRATIVE_FIELDS:
        value = (record.get(field) or "").strip() if isinstance(record.get(field), str) else ""
        if len(value) < MIN_FIELD_LENGTH:
            problems.append({
                "field": field,
                "issue": f"mandatory field must be at least {MIN_FIELD_LENGTH} characters",
            })
    return problems


def can_transition(current: str, target: str) -> bool:
    return target in STR_STATUS_TRANSITIONS.get(current, set())


def canonical_content(record: dict) -> str:
    """Stable text representation used for the evidentiary content hash."""
    parts = [f"str_id={record.get('str_id')}", f"case_id={record.get('case_id')}"]
    for field in STR_NARRATIVE_FIELDS:
        parts.append(f"{field}={(record.get(field) or '').strip()}")
    return "\n".join(parts)


def content_sha256(record: dict) -> str:
    return hashlib.sha256(canonical_content(record).encode("utf-8")).hexdigest()


def build_str_pdf(record: dict) -> bytes:
    """Render an STR export PDF. The content SHA-256 is embedded in the PDF
    metadata and serves as the integrity anchor for future digital signing
    (HSM/PKI signing can be layered on the same digest)."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
        title=f"STR {record.get('str_id')} — JFIU Export",
    )
    styles = getSampleStyleSheet()
    story = [
        Paragraph("Suspicious Transaction Report — JFIU Export", styles["Title"]),
        Paragraph("Overwatch AML Platform (regulatory draft export)", styles["Normal"]),
        Spacer(1, 8 * mm),
    ]

    meta = [
        ["STR ID", str(record.get("str_id"))],
        ["Case ID", str(record.get("case_id") or "—")],
        ["Status", str(record.get("status"))],
        ["Created", str(record.get("created_at"))],
        ["Submitted", str(record.get("submitted_at") or "—")],
        ["Content SHA-256", content_sha256(record)],
    ]
    table = Table(meta, colWidths=[38 * mm, 118 * mm])
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f0f0f0")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
    ]))
    story += [table, Spacer(1, 8 * mm)]

    titles = {
        "triggering_factors": "1. Triggering Factors",
        "subject_background": "2. Subject Background",
        "digital_footprints": "3. Digital Footprints",
        "transaction_summary": "4. Transaction Summary",
    }
    for field in STR_NARRATIVE_FIELDS:
        story.append(Paragraph(titles[field], styles["Heading3"]))
        story.append(Paragraph(
            (record.get(field) or "—").replace("&", "&amp;").replace("<", "&lt;").replace("\n", "<br/>"),
            styles["Normal"],
        ))
        story.append(Spacer(1, 5 * mm))

    doc.build(story)
    return buf.getvalue()
