"""Build the two-page PromoScout solution document with ReportLab."""

from __future__ import annotations

import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf" / "PromoScout_Solution_Doc.pdf"

INK = colors.HexColor("#10213F")
MUTED = colors.HexColor("#5D6F8C")
PURPLE = colors.HexColor("#2563EB")
PURPLE_DARK = colors.HexColor("#123B8F")
PURPLE_PALE = colors.HexColor("#EEF5FF")
PINK = colors.HexColor("#3B82F6")
PINK_PALE = colors.HexColor("#F7FAFF")
TEAL = colors.HexColor("#1D4ED8")
TEAL_PALE = colors.HexColor("#F1F6FF")
GOLD_PALE = colors.HexColor("#F8FBFF")
LINE = colors.HexColor("#D6E2F4")
WHITE = colors.white


def register_fonts():
    font_dir = ROOT / "assets" / "fonts"
    for name in ("Regular", "Medium", "SemiBold", "Bold"):
        pdfmetrics.registerFont(TTFont(f"Inter-{name}", font_dir / f"Inter-{name}.ttf"))
    pdfmetrics.registerFontFamily(
        "Inter",
        normal="Inter-Regular",
        bold="Inter-Bold",
        italic="Inter-Regular",
        boldItalic="Inter-SemiBold",
    )


def p(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(text, style)


def box(title: str, body: str, styles, background=PURPLE_PALE, accent=PURPLE):
    content = [
        p(title, styles["box_title"]),
        Spacer(1, 3),
        p(body, styles["box_body"]),
    ]
    table = Table([[content]], colWidths=[3.47 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), background),
                ("BOX", (0, 0), (-1, -1), 0.6, LINE),
                ("LINEBEFORE", (0, 0), (0, -1), 4, accent),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return table


def section_heading(number: str, title: str, styles):
    return KeepTogether(
        [
            Spacer(1, 3),
            p(f"<font color='{PURPLE.hexval()}'>{number}</font>  {title}", styles["section"]),
            Spacer(1, 5),
        ]
    )


def bullet(text: str, styles, color=PURPLE):
    return p(f"<font color='{color.hexval()}'><b>-</b></font>  {text}", styles["bullet"])


def footer(canvas, doc):
    canvas.saveState()
    width, _ = letter
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.5)
    canvas.line(36, 28, width - 36, 28)
    canvas.setFont("Inter-Medium", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(36, 16, "PROMOSCOUT  |  KUKU AI GENERALIST ASSIGNMENT  |  PROBLEM 1")
    canvas.drawRightString(width - 36, 16, f"{doc.page:02d} / 02")
    canvas.restoreState()


def build_styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "Title",
            parent=base["Title"],
            fontName="Inter-Bold",
            fontSize=23,
            leading=25,
            textColor=INK,
            alignment=TA_LEFT,
            spaceAfter=2,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle",
            parent=base["Normal"],
            fontName="Inter-Regular",
            fontSize=9.5,
            leading=13,
            textColor=MUTED,
        ),
        "kicker": ParagraphStyle(
            "Kicker",
            parent=base["Normal"],
            fontName="Inter-SemiBold",
            fontSize=7.5,
            leading=9,
            textColor=PURPLE_DARK,
            tracking=1.2,
        ),
        "section": ParagraphStyle(
            "Section",
            parent=base["Heading2"],
            fontName="Inter-Bold",
            fontSize=11.5,
            leading=13,
            textColor=INK,
            spaceAfter=0,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["BodyText"],
            fontName="Inter-Regular",
            fontSize=8.3,
            leading=11.2,
            textColor=INK,
            spaceAfter=4,
        ),
        "small": ParagraphStyle(
            "Small",
            parent=base["BodyText"],
            fontName="Inter-Regular",
            fontSize=7.4,
            leading=9.6,
            textColor=MUTED,
        ),
        "box_title": ParagraphStyle(
            "BoxTitle",
            parent=base["Heading3"],
            fontName="Inter-SemiBold",
            fontSize=9.1,
            leading=11,
            textColor=INK,
        ),
        "box_body": ParagraphStyle(
            "BoxBody",
            parent=base["BodyText"],
            fontName="Inter-Regular",
            fontSize=7.6,
            leading=10,
            textColor=INK,
        ),
        "bullet": ParagraphStyle(
            "Bullet",
            parent=base["BodyText"],
            fontName="Inter-Regular",
            fontSize=7.7,
            leading=10.1,
            textColor=INK,
            leftIndent=1,
            firstLineIndent=0,
            spaceAfter=2.5,
        ),
        "metric_num": ParagraphStyle(
            "MetricNum",
            parent=base["Normal"],
            fontName="Inter-Bold",
            fontSize=15,
            leading=16,
            textColor=PURPLE_DARK,
            alignment=TA_CENTER,
        ),
        "metric_label": ParagraphStyle(
            "MetricLabel",
            parent=base["Normal"],
            fontName="Inter-SemiBold",
            fontSize=6.8,
            leading=8.2,
            textColor=MUTED,
            alignment=TA_CENTER,
        ),
        "quote": ParagraphStyle(
            "Quote",
            parent=base["BodyText"],
            fontName="Inter-SemiBold",
            fontSize=8.1,
            leading=10.6,
            textColor=INK,
        ),
    }


def build():
    register_fonts()
    metrics = json.loads(
        (ROOT / "artifacts" / "step8" / "quality_metrics.json").read_text(encoding="utf-8")
    )
    shortlist = json.loads(
        (ROOT / "artifacts" / "step8" / "reviewed_shortlist.json").read_text(encoding="utf-8")
    )
    top = shortlist[0]
    styles = build_styles()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    doc = BaseDocTemplate(
        str(OUTPUT),
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=32,
        bottomMargin=38,
        title="PromoScout - Kuku AI Generalist Assignment",
        author="PromoScout",
        subject="Problem 1: Find the Promos (Ads)",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
    doc.addPageTemplates([PageTemplate(id="two-page", frames=[frame], onPage=footer)])

    story = []
    story.extend(
        [
            p("PROBLEM 1  /  FIND THE PROMOS (ADS)", styles["kicker"]),
            Spacer(1, 3),
            p("PromoScout", styles["title"]),
            p(
                "An AI-assisted editor tool that turns timestamped microdrama screenplays into source-grounded, ranked 20-60 second promo recommendations.",
                styles["subtitle"],
            ),
            Spacer(1, 9),
        ]
    )

    problem_box = box(
        "THE PROBLEM",
        "Editors currently watch every episode and find promo moments by hand. That does not scale as new shows arrive weekly. The output must hook within 3 seconds, end unresolved, and make sense to a new viewer.",
        styles,
        PINK_PALE,
        PINK,
    )
    choice_box = box(
        "WHY THIS PROBLEM",
        "It has a real repetitive workflow, supplied ground-truth timestamps, and a testable output. I scoped the prototype to continuous single-episode clips; stitched promos are a later extension.",
        styles,
        TEAL_PALE,
        TEAL,
    )
    two_col = Table([[problem_box, choice_box]], colWidths=[3.58 * inch, 3.58 * inch], hAlign="LEFT")
    two_col.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 7)]))
    story.extend([two_col, Spacer(1, 9)])

    story.append(section_heading("01", "HOW IT WORKS", styles))
    steps = [
        ("1", "PARSE", "Read ZIP/TXT, normalize labels, validate every timestamp."),
        ("2", "GENERATE", "Create 20-60s windows around action, dialogue, reveals, and episode endings."),
        ("3", "EVALUATE", "Gemini scores hook, cliffhanger, standalone clarity, intensity, and risk."),
        ("4", "VALIDATE", "Code rejects invalid cuts, false hooks, weak endings, and duplicates."),
        ("5", "REVIEW", "Editor inspects source, accepts/rejects, and exports JSON/CSV/Markdown."),
    ]
    step_cells = []
    for number, label, body in steps:
        step_cells.append(
            [
                p(f"<font color='{PURPLE.hexval()}'><b>{number}</b></font>  <b>{label}</b>", styles["box_title"]),
                p(body, styles["small"]),
            ]
        )
    step_table = Table([step_cells], colWidths=[1.43 * inch] * 5)
    step_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7FAFF")),
                ("BOX", (0, 0), (-1, -1), 0.6, LINE),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    story.extend([step_table, Spacer(1, 9)])

    story.append(section_heading("02", "WHAT AI DOES - AND WHAT IT DOES NOT", styles))
    responsibility_data = [
        [p("PYTHON / RULES", styles["box_title"]), p("GEMINI", styles["box_title"]), p("HUMAN EDITOR", styles["box_title"])],
        [
            p("Parsing, timestamps, duration, candidate windows, schema validation, penalties, deduplication, diversity, exports.", styles["box_body"]),
            p("Semantic judgment: hook, unresolved ending, standalone clarity, emotional/visual potential, warnings.", styles["box_body"]),
            p("Checks actual footage, acting, pacing, spoilers, brand safety, and makes the final publishing decision.", styles["box_body"]),
        ],
    ]
    resp_table = Table(responsibility_data, colWidths=[2.38 * inch] * 3)
    resp_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), PURPLE_PALE),
                ("BOX", (0, 0), (-1, -1), 0.6, LINE),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.extend([resp_table, Spacer(1, 9)])

    story.append(section_heading("03", "EXAMPLE OUTPUT", styles))
    example_left = [
        p(f"<b>#{top['reviewed_rank']}  EPISODE {top['episode']}</b>", styles["box_title"]),
        p(
            f"<font color='{PURPLE_DARK.hexval()}'><b>{top['start_timestamp']} - {top['end_timestamp']}</b></font>  |  {top['duration_seconds']:.1f}s",
            styles["body"],
        ),
        p(f"<b>Hook:</b> {top['hook']}", styles["box_body"]),
    ]
    example_right = [
        p(f"<b>Cliffhanger:</b> {top['cliffhanger']}", styles["box_body"]),
        Spacer(1, 3),
        p(f"<b>Why it works:</b> {top['why_it_works']}", styles["box_body"]),
    ]
    example = Table([[example_left, example_right]], colWidths=[2.65 * inch, 4.5 * inch])
    example.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), GOLD_PALE),
                ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#AFC8F5")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.extend(
        [
            example,
            Spacer(1, 6),
            p(
                "Assumptions: screenplay timestamps are authoritative; continuous clips are the MVP; actual footage is unavailable; the system shortlists rather than publishes.",
                styles["small"],
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            p("MEASURED ON THE FULL 50-EPISODE PACK", styles["kicker"]),
            Spacer(1, 3),
            p("Results, failures, and scale", styles["title"]),
            p(
                "Every claim below comes from the saved full-pack run and a manual screenplay review of all 15 primary recommendations plus 8 additional examples.",
                styles["subtitle"],
            ),
            Spacer(1, 9),
        ]
    )

    metrics_data = [
        [
            [p("50/50", styles["metric_num"]), p("EPISODES PARSED", styles["metric_label"])],
            [p("232", styles["metric_num"]), p("CANDIDATE WINDOWS", styles["metric_label"])],
            [p("100/100", styles["metric_num"]), p("GEMINI OUTPUTS VALID", styles["metric_label"])],
            [p("86.7%", styles["metric_num"]), p("SHORTLIST-WORTHY TOP 15", styles["metric_label"])],
        ]
    ]
    metrics_table = Table(metrics_data, colWidths=[1.79 * inch] * 4)
    metrics_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7FAFF")),
                ("BOX", (0, 0), (-1, -1), 0.6, LINE),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, LINE),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.extend([metrics_table, Spacer(1, 8)])

    story.append(section_heading("04", "QUALITY CHECK", styles))
    quality_left = [
        p("MANUAL TOP-15 REVIEW", styles["box_title"]),
        bullet("11 strong as-is (73.3%).", styles, TEAL),
        bullet("2 plausible but need boundary/editor review.", styles, colors.HexColor("#4F7FC8")),
        bullet("2 false positives (13.3%).", styles, PINK),
        bullet("13/15 shortlist-worthy (86.7%).", styles, PURPLE),
    ]
    quality_right = [
        p("FULL PIPELINE", styles["box_title"]),
        bullet("0 parser errors; 1 retained source warning.", styles, TEAL),
        bullet("65 suitable / 17 borderline / 18 Gemini rejects.", styles, PURPLE),
        bullet("35 quality rejections + 8 weaker same-episode duplicates.", styles, PINK),
        bullet("15 primary promos: exactly 3 from each story arc.", styles, PURPLE),
    ]
    quality_table = Table([[quality_left, quality_right]], colWidths=[3.58 * inch, 3.58 * inch])
    quality_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, 0), TEAL_PALE),
                ("BACKGROUND", (1, 0), (1, 0), PURPLE_PALE),
                ("BOX", (0, 0), (-1, -1), 0.6, LINE),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    story.extend([quality_table, Spacer(1, 8)])

    story.append(section_heading("05", "WHERE IT FAILS", styles))
    failure_data = [
        [
            p("FALSE CLIFFHANGER", styles["box_title"]),
            p("Episode 10 opens with a bloody entrance but ends on the soft question 'Does it hurt?'. Gemini overvalued romantic tension.", styles["box_body"]),
        ],
        [
            p("FALSE HOOK", styles["box_title"]),
            p("Episode 22 ends strongly, but its first 3 seconds are mansion awe and 'This house...' - not a scroll-stopper.", styles["box_body"]),
        ],
        [
            p("BOUNDARY MISS", styles["box_title"]),
            p("A high-scoring Episode 3 fight cut ends before the actual proposal. Gemini correctly rejected it, proving the second stage is necessary.", styles["box_body"]),
        ],
    ]
    failure_table = Table(failure_data, colWidths=[1.25 * inch, 5.9 * inch])
    failure_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), PINK_PALE),
                ("BOX", (0, 0), (-1, -1), 0.6, LINE),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.extend([failure_table, Spacer(1, 8)])

    story.append(section_heading("06", "SCALE, COST, AND SUCCESS", styles))
    scale_box = box(
        "SCALE + COST CONTROL",
        "Local rules reduced 232 windows to 100 Gemini calls (top 2 per episode). Responses are cached and resumable. The free tier required 4.5s throttling; the complete run took about 6.5 minutes. Model name and limits are configuration, not code changes.",
        styles,
        PURPLE_PALE,
        PURPLE,
    )
    success_box = box(
        "WHAT I WOULD MEASURE NEXT",
        "Editor acceptance, minutes saved per episode, boundary-adjustment rate, duplicates, and cost per show - then 3-second hold, completion, click-through, and installs versus editor-selected promos in an A/B pilot.",
        styles,
        TEAL_PALE,
        TEAL,
    )
    scale_table = Table([[scale_box, success_box]], colWidths=[3.58 * inch, 3.58 * inch])
    scale_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 7)]))
    story.extend([scale_table, Spacer(1, 8)])

    ai_note = Table(
        [[p("AI USE", styles["box_title"]), p("Gemini 3.5 Flash Lite provided structured semantic judgments. AI helped build/debug the prototype and draft this document; all metrics come from saved runs. The decisions, manual review, and failure analysis are mine. No claim predicts real views or installs.", styles["box_body"])]],
        colWidths=[0.8 * inch, 6.35 * inch],
    )
    ai_note.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7FAFF")),
                ("BOX", (0, 0), (-1, -1), 0.6, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    story.extend(
        [
            ai_note,
            Spacer(1, 6),
            p(
                "Core limitation: screenplay text cannot reveal acting, final footage quality, shot rhythm, audio impact, or platform performance. A real editor remains in the loop.",
                styles["small"],
            ),
        ]
    )

    doc.build(story)
    print(OUTPUT)


if __name__ == "__main__":
    build()

