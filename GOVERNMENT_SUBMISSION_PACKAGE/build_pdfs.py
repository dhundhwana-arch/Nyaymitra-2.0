#!/usr/bin/env python3
"""Build professional PDFs from the markdown sources in sources/."""
import os
import re
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer,
    Table, TableStyle, HRFlowable, PageBreak, KeepTogether,
)

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "sources"
OUT = ROOT

NAVY = colors.HexColor("#1a3a5c")
STEEL = colors.HexColor("#33658a")
LIGHT = colors.HexColor("#eef3f8")
GREY = colors.HexColor("#5a5a5a")
RULE = colors.HexColor("#c9d4e0")

PAGE_W, PAGE_H = A4
MARGIN = 18 * mm

# ----------------------------------------------------------------------------- styles
def st(name, **kw):
    base = dict(
        fontName="Helvetica", fontSize=9.5, leading=13.5,
        textColor=colors.HexColor("#1a1a1a"), alignment=TA_JUSTIFY,
        spaceAfter=6,
    )
    base.update(kw)
    return ParagraphStyle(name, **base)

S_TITLE = st("title", fontName="Helvetica-Bold", fontSize=21, leading=26,
             textColor=NAVY, alignment=TA_LEFT, spaceAfter=2)
S_SUB = st("sub", fontSize=11.5, leading=16, textColor=STEEL, alignment=TA_LEFT, spaceAfter=10)
S_H1 = st("h1", fontName="Helvetica-Bold", fontSize=14, leading=18, textColor=NAVY,
          alignment=TA_LEFT, spaceBefore=14, spaceAfter=6)
S_H2 = st("h2", fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=STEEL,
          alignment=TA_LEFT, spaceBefore=10, spaceAfter=4)
S_H3 = st("h3", fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=STEEL,
          alignment=TA_LEFT, spaceBefore=10, spaceAfter=4)
S_BODY = st("body")
S_BODY_L = st("bodyL", alignment=TA_LEFT)
S_BULLET = st("bullet", leftIndent=14, bulletIndent=4, spaceAfter=3, alignment=TA_LEFT)
S_SMALL = st("small", fontSize=8, leading=10.5, textColor=GREY, alignment=TA_LEFT, spaceAfter=3)
S_CELL = st("cell", fontSize=8, leading=10, alignment=TA_LEFT, spaceAfter=0)
S_CELL_B = st("cellB", fontName="Helvetica-Bold", fontSize=8, leading=10,
              alignment=TA_LEFT, textColor=NAVY, spaceAfter=0)
S_HEADER = st("header", fontSize=8, leading=10, textColor=GREY, alignment=TA_LEFT, spaceAfter=0)
S_FOOTER = st("footer", fontSize=7.5, leading=10, textColor=GREY, alignment=TA_CENTER, spaceAfter=0)


def inline(text):
    """Very small markdown inline: **bold**."""
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"\*(.+?)\*", r"<i>\1</i>", text)
    return text


def parse_blocks(md):
    """Convert simple markdown to a list of flowables."""
    flowables = []
    lines = md.split("\n")
    i = 0
    while i < len(lines):
        raw = lines[i]
        line = raw.rstrip()

        # Horizontal rule
        if re.match(r"^[-*_]{3,}\s*$", line):
            flowables.append(HRFlowable(width="100%", thickness=0.7, color=RULE,
                                        spaceBefore=6, spaceAfter=8))
            i += 1
            continue

        # Page break marker
        if line.strip() == "---" and i > 0 and lines[i-1].strip() == "":
            flowables.append(PageBreak())
            i += 1
            continue

        # Heading 1
        m = re.match(r"^#\s+(.+)$", line)
        if m:
            flowables.append(Paragraph(inline(m.group(1)), S_H1))
            i += 1
            continue
        # Heading 2
        m = re.match(r"^##\s+(.+)$", line)
        if m:
            flowables.append(Paragraph(inline(m.group(1)), S_H2))
            i += 1
            continue
        # Heading 3
        m = re.match(r"^###\s+(.+)$", line)
        if m:
            flowables.append(Paragraph(inline(m.group(1)), S_H3))
            i += 1
            continue
        # Table (pipe-delimited)
        if line.strip().startswith("|") and line.strip().endswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                rows.append(cells)
                i += 1
            # skip separator row if it's all dashes/colons
            if rows and all(set(c) <= set(":- |") for c in rows[1]):
                rows.pop(1)
            flowables.extend(make_table(rows))
            continue
        # List item
        m = re.match(r"^[-*]\s+(.+)$", line)
        if m:
            flowables.append(Paragraph("&bull; " + inline(m.group(1)), S_BULLET))
            i += 1
            continue
        # Blank line
        if line.strip() == "":
            flowables.append(Spacer(1, 4))
            i += 1
            continue
        # Paragraph (collect consecutive non-blank, non-special lines)
        buf = []
        while i < len(lines) and lines[i].strip() != "" and not lines[i].strip().startswith("#") \
                and not lines[i].strip().startswith("|") and not re.match(r"^[-*]\s+", lines[i]) \
                and not re.match(r"^[-*_]{3,}\s*$", lines[i]) and lines[i].strip() != "---":
            buf.append(lines[i])
            i += 1
        if buf:
            flowables.append(Paragraph(inline(" ".join(buf)), S_BODY))
    return flowables


def make_table(rows):
    if not rows:
        return Spacer(1, 4)
    # header row bold + navy fill
    data = [[Paragraph(inline(c), S_CELL_B) for c in rows[0]]]
    for r in rows[1:]:
        data.append([Paragraph(inline(c), S_CELL) for c in r])
    t = Table(data, repeatRows=1, hAlign="LEFT")
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.4, RULE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
    ]
    t.setStyle(TableStyle(style))
    return [t, Spacer(1, 8)]


# ----------------------------------------------------------------------------- page furniture
def on_page(canvas, doc):
    canvas.saveState()
    # header rule
    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.5)
    canvas.line(MARGIN, PAGE_H - 14 * mm, PAGE_W - MARGIN, PAGE_H - 14 * mm)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(GREY)
    canvas.drawString(MARGIN, PAGE_H - 12 * mm, "NYAYMITRA 2.0 — Government Submission Package")
    canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - 12 * mm,
                           "AI-Powered Inclusive Justice Access & Navigation System")
    # footer
    canvas.line(MARGIN, 13 * mm, PAGE_W - MARGIN, 13 * mm)
    canvas.drawString(MARGIN, 10 * mm, "Functional software prototype / Proof of Concept — not legal advice")
    canvas.drawRightString(PAGE_W - MARGIN, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


def build_pdf(src_path, out_path, title_text, sub_text):
    doc = BaseDocTemplate(str(out_path), pagesize=A4,
                          leftMargin=MARGIN, rightMargin=MARGIN,
                          topMargin=22 * mm, bottomMargin=18 * mm,
                          title=title_text, author="NYAYMITRA 2.0")
    frame = Frame(MARGIN, 18 * mm, PAGE_W - 2 * MARGIN, PAGE_H - 22 * mm - 18 * mm, id="main")
    doc.addPageTemplates([PageTemplate(id="page", frames=[frame], onPage=on_page)])

    md = src_path.read_text(encoding="utf-8")
    # extract optional leading title override
    story = []
    story.append(Paragraph(inline(title_text), S_TITLE))
    story.append(Spacer(1, 2))
    story.append(Paragraph(inline(sub_text), S_SUB))
    story.append(HRFlowable(width="100%", thickness=1, color=NAVY, spaceBefore=2, spaceAfter=10))
    story.extend(parse_blocks(md))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=0.7, color=RULE, spaceBefore=4, spaceAfter=4))
    story.append(Paragraph(
        "NYAYMITRA 2.0 — functional software prototype / Proof of Concept — subject to independent evaluation. "
        "Not legal advice; not a replacement for courts, lawyers, police, or government authorities. "
        "https://github.com/dhundhwana-arch/Nyaymitra-2.0 (branch arena/812d6894-nyaymitra-2-0, commit cc56d0e)",
        S_FOOTER))

    doc.build(story)
    return out_path


DOCS = [
    ("Executive_Summary.md", "NYAYMITRA 2.0 — Executive Summary",
     "Government-facing overview of the AI-Powered Inclusive Justice Access & Navigation System"),
    ("NYAYMITRA_2.0_Project_Report.md", "NYAYMITRA 2.0 — Project Report",
     "Problem, solution, beneficiaries, technology, architecture, status, roadmap"),
    ("Technical_Architecture_Report.md", "NYAYMITRA 2.0 — Technical Architecture Report",
     "Frontend, backend, database, AI/RAG, data flow, API, security, deployment, limitations"),
    ("Prototype_Progress_Report.md", "NYAYMITRA 2.0 — Prototype Progress and Evidence Report",
     "Implemented, tested, demonstrated, incomplete, test outputs, commit references"),
    ("Legal_Privacy_Safety_Report.md", "NYAYMITRA 2.0 — Legal, Privacy and Safety Readiness Report",
     "Legal advice vs information, human review, data protection, AI data flow, DPDP, risks"),
    ("Development_Roadmap.md", "NYAYMITRA 2.0 — Development Roadmap",
     "Completed work, remaining work, institutional support, milestones, resources"),
    ("Risk_Register.md", "NYAYMITRA 2.0 — Risk Register",
     "Technical, legal, privacy, security, operational, and adoption risks with mitigations"),
    ("Government_Pitch_Deck.md", "NYAYMITRA 2.0 — Government Pitch Deck",
     "8–10 slide presentation: title, problem, solution, innovation, prototype, architecture, impact, roadmap, request"),
    ("Demo_Script.md", "NYAYMITRA 2.0 — Demo Script",
     "Three citizen journeys with synthetic data: legal question, sources, department/human assistance"),
    ("Submission_Checklist.md", "NYAYMITRA 2.0 — Submission Checklist",
     "SSIP / Startup Srujan application fields, supporting documents, declarations, approvals"),
]


def main():
    built = []
    for fname, title, sub in DOCS:
        src = SRC / fname
        out = OUT / (fname.replace(".md", ".pdf"))
        build_pdf(src, out, title, sub)
        built.append(out)
        print(f"PDF: {out}")
    print(f"\nBuilt {len(built)} PDFs in {OUT}")


if __name__ == "__main__":
    main()
