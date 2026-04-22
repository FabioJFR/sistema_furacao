from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


ROOT = Path(__file__).resolve().parent
INPUT_FILE = ROOT / "drone_proprio_componentes.md"
OUTPUT_FILE = ROOT / "drone_proprio_componentes.pdf"


def build_styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="DocTitle",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=24,
            textColor=colors.HexColor("#0f172a"),
            spaceAfter=10,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Section",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            textColor=colors.HexColor("#0f172a"),
            spaceBefore=10,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BodyDoc",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=10.5,
            leading=15,
            textColor=colors.HexColor("#1f2937"),
            alignment=TA_LEFT,
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BulletDoc",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=10.5,
            leading=15,
            leftIndent=12,
            bulletIndent=0,
            textColor=colors.HexColor("#1f2937"),
            spaceAfter=3,
        )
    )
    return styles


def markdown_to_story(text, styles):
    story = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            story.append(Spacer(1, 4))
            continue

        if line.startswith("# "):
            story.append(Paragraph(_escape(line[2:]), styles["DocTitle"]))
            continue
        if line.startswith("## "):
            story.append(Paragraph(_escape(line[3:]), styles["Section"]))
            continue
        if line.startswith("### "):
            story.append(Paragraph(f"<b>{_escape(line[4:])}</b>", styles["BodyDoc"]))
            continue
        if line.startswith("- "):
            story.append(Paragraph(_escape(line[2:]), styles["BulletDoc"], bulletText="•"))
            continue
        if _looks_like_numbered(line):
            number, content = line.split(". ", 1)
            story.append(Paragraph(_escape(content), styles["BulletDoc"], bulletText=f"{number}."))
            continue

        story.append(Paragraph(_escape(line), styles["BodyDoc"]))
    return story


def _looks_like_numbered(line):
    if ". " not in line:
        return False
    prefix = line.split(". ", 1)[0]
    return prefix.isdigit()


def _escape(text):
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def main():
    styles = build_styles()
    content = INPUT_FILE.read_text(encoding="utf-8")
    doc = SimpleDocTemplate(
        str(OUTPUT_FILE),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title="Relatorio Tecnico - Drone proprio integrado com a plataforma",
        author="Codex",
    )
    story = markdown_to_story(content, styles)
    doc.build(story)
    print(OUTPUT_FILE)


if __name__ == "__main__":
    main()
