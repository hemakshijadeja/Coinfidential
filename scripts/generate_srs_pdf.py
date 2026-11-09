"""Convert docs/SRS.md into SRS_Stage1_Submission.pdf at the repository root.

Supports the Markdown that the SRS uses: headings, paragraphs, nested lists,
tables, fenced code blocks, horizontal rules, and inline code, bold, links and
[[wikilinks]]. Text outside this subset is rendered as plain paragraphs.

The built-in PDF fonts cover only Latin text, so a character they cannot show
stops the build instead of printing as a black box.
"""

import re
import sys
import textwrap
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    HRFlowable,
    KeepTogether,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Preformatted,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = ROOT / "docs" / "SRS.md"
DEFAULT_OUTPUT = ROOT / "SRS_Stage1_Submission.pdf"

MARGIN = 18 * mm
CONTENT_WIDTH = A4[0] - 2 * MARGIN
NAVY = colors.HexColor("#1F3A5F")
BLUE = colors.HexColor("#1F5FA8")
GREY = colors.HexColor("#5A6472")
LIGHT = colors.HexColor("#F2F5F9")
RULE = colors.HexColor("#C9D2DC")
CODE_COLOR = "#8A2B4F"
CODE_LINE_LENGTH = 96
KEEP_TOGETHER_LINES = 30
CELL_FONT_SIZE = 7.8
CELL_PADDING = 4
MAX_WORD_COLUMN_SHARE = 0.3
LINE_BREAK = "\x01"

BODY = ParagraphStyle("Body", fontName="Helvetica", fontSize=9.5, leading=13.5, spaceAfter=6)
STYLES = {
    "body": BODY,
    "title": ParagraphStyle("Title", parent=BODY, fontName="Helvetica-Bold", fontSize=26, leading=32, textColor=NAVY, alignment=TA_CENTER, spaceAfter=14),
    "cover": ParagraphStyle("Cover", parent=BODY, fontSize=13, leading=20, textColor=GREY, alignment=TA_CENTER, spaceAfter=10),
    "h2": ParagraphStyle("H2", parent=BODY, fontName="Helvetica-Bold", fontSize=17, leading=22, textColor=NAVY, spaceAfter=10, keepWithNext=1),
    "h3": ParagraphStyle("H3", parent=BODY, fontName="Helvetica-Bold", fontSize=12.5, leading=16, textColor=NAVY, spaceBefore=10, spaceAfter=6, keepWithNext=1),
    "h4": ParagraphStyle("H4", parent=BODY, fontName="Helvetica-Bold", fontSize=10, leading=13, textColor=GREY, spaceBefore=7, spaceAfter=3, keepWithNext=1),
    "cell": ParagraphStyle("Cell", parent=BODY, fontSize=7.8, leading=10, spaceAfter=0),
    "header": ParagraphStyle("Header", parent=BODY, fontName="Helvetica-Bold", fontSize=7.8, leading=10, textColor=colors.white, spaceAfter=0),
    "code": ParagraphStyle("Code", fontName="Courier", fontSize=7.8, leading=10, backColor=LIGHT, borderPadding=5, spaceBefore=6, spaceAfter=10, leftIndent=5, rightIndent=5),
    "toc_title": ParagraphStyle("TocTitle", parent=BODY, fontName="Helvetica-Bold", fontSize=17, leading=22, textColor=NAVY, spaceAfter=12),
    "toc0": ParagraphStyle("Toc0", parent=BODY, fontName="Helvetica-Bold", fontSize=10, leading=15, spaceBefore=5, spaceAfter=0),
    "toc1": ParagraphStyle("Toc1", parent=BODY, fontSize=9, leading=12.5, leftIndent=12, spaceAfter=0),
}

CODE_SPAN = re.compile(r"`([^`]+)`")
BOLD = re.compile(r"\*\*(.+?)\*\*")
LINK = re.compile(r"\[([^\]\[]+)\]\((https?://[^)\s]+|[^)\s]+)\)")
WIKILINK = re.compile(r"\[\[([^\]\n]+)\]\]")
HEADING = re.compile(r"(#{1,4})\s+(.*)")
LIST_ITEM = re.compile(r"(\s*)([-*]|\d+\.)\s+(.*)")
TABLE_DIVIDER = re.compile(r"\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?\s*")
NUMBERED = re.compile(r"\d+\.")


def format_inline(text: str, code_size: float | None = None) -> str:
    """Convert inline Markdown to the markup that ReportLab paragraphs accept."""
    spans: list[str] = []

    def hold_code(match: re.Match[str]) -> str:
        size = f' size="{code_size}"' if code_size else ""
        spans.append(f'<font face="Courier"{size} color="{CODE_COLOR}">{escape(match.group(1))}</font>')
        return f"\0{len(spans) - 1}\0"

    result = escape(CODE_SPAN.sub(hold_code, text))
    result = WIKILINK.sub(lambda m: f'<font color="#1F5FA8">[[{m.group(1)}]]</font>', result)
    result = LINK.sub(lambda m: _format_link(m.group(1), m.group(2)), result)
    result = BOLD.sub(r"<b>\1</b>", result)
    return re.sub(r"\0(\d+)\0", lambda m: spans[int(m.group(1))], result)


def _format_link(label: str, target: str) -> str:
    if target.startswith("http"):
        return f'<a href="{target}" color="#1F5FA8">{label}</a>'
    return label


def split_table_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def text_width(text: str, font: str = "Helvetica-Bold") -> float:
    return stringWidth(text, font, CELL_FONT_SIZE)


def longest_word_width(cell: str) -> float:
    """Return the width of the longest piece of a cell that cannot wrap."""
    # Wikilinks can wrap at their hyphens, so only their parts have to fit.
    plain = WIKILINK.sub(lambda m: m.group(1).replace("-", " "), cell).replace("`", "").replace("*", "")
    return max((text_width(word) for word in plain.split()), default=0.0)


def column_widths(rows: list[list[str]]) -> list[float]:
    """Share the page by text length, keeping whole words inside their columns."""
    count = len(rows[0])
    minimums = []
    weights = []
    for column in range(count):
        cells = [row[column] for row in rows if column < len(row)]
        lengths = [len(cell) for cell in cells]
        weights.append((sum(lengths) / len(lengths) + max(lengths) * 0.4) ** 0.75)
        word_limit = CONTENT_WIDTH * MAX_WORD_COLUMN_SHARE
        minimums.append(min(max(longest_word_width(cell) for cell in cells) + CELL_PADDING * 2 + 1, word_limit))

    available = CONTENT_WIDTH - sum(minimums)
    if available <= 0:
        scale = sum(minimums)
        return [CONTENT_WIDTH * minimum / scale for minimum in minimums]

    # Give spare width to the columns that need it most, without shrinking any.
    widths = minimums[:]
    total_weight = sum(weights)
    targets = [CONTENT_WIDTH * weight / total_weight for weight in weights]
    needs = [max(target - minimum, 0.0) for target, minimum in zip(targets, minimums, strict=True)]
    total_need = sum(needs) or 1.0
    for column in range(count):
        widths[column] += available * needs[column] / total_need
    return widths


def wrap_wikilinks(cell: str, width: float) -> str:
    """Break a wikilink at its hyphens when it is wider than its column."""

    def wrap(match: re.Match[str]) -> str:
        link = match.group(0)
        limit = width - CELL_PADDING * 2 - 1
        if text_width(link, "Helvetica") <= limit:
            return link
        lines = [""]
        parts = link.split("-")
        for position, part in enumerate(parts):
            piece = part + ("-" if position < len(parts) - 1 else "")
            if lines[-1] and text_width(lines[-1] + piece, "Helvetica") > limit:
                lines.append("")
            lines[-1] += piece
        return LINE_BREAK.join(lines)

    return WIKILINK.sub(wrap, cell)


def build_table(rows: list[list[str]]) -> Table:
    count = len(rows[0])
    widths = column_widths(rows)
    data = []
    for row_number, row in enumerate(rows):
        style = STYLES["header"] if row_number == 0 else STYLES["cell"]
        cells = (row + [""] * count)[:count]
        if row_number == 0:
            # The code color cannot be read on the dark header background.
            cells = [cell.replace("`", "") for cell in cells]
        data.append(
            [
                Paragraph(format_inline(wrap_wikilinks(cell, width), code_size=7.2).replace(LINE_BREAK, "<br/>"), style)
                for cell, width in zip(cells, widths, strict=True)
            ]
        )
    table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT", spaceBefore=4, spaceAfter=10)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
                ("GRID", (0, 0), (-1, -1), 0.4, RULE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return table


def build_code_block(lines: list[str]) -> Preformatted | KeepTogether:
    wrapped: list[str] = []
    for line in lines:
        wrapped.extend(
            textwrap.wrap(
                line,
                CODE_LINE_LENGTH,
                subsequent_indent="    ",
                drop_whitespace=False,
                break_long_words=True,
                replace_whitespace=False,
            )
            or [""]
        )
    block = Preformatted("\n".join(wrapped), STYLES["code"])
    return KeepTogether([block]) if len(wrapped) <= KEEP_TOGETHER_LINES else block


def build_list_item(indent: str, marker: str, text: str) -> Paragraph:
    depth = len(indent) // 2
    left_indent = 14 + depth * 14
    style = ParagraphStyle(f"List{depth}", parent=BODY, leftIndent=left_indent, bulletIndent=left_indent - 11, spaceAfter=3)
    bullet = marker if NUMBERED.fullmatch(marker) else "•"
    return Paragraph(format_inline(text), style, bulletText=bullet)


class SrsDocument(BaseDocTemplate):
    """A document that records headings for the contents page and PDF outline."""

    def __init__(self, filename: str, title: str) -> None:
        super().__init__(
            filename,
            pagesize=A4,
            leftMargin=MARGIN,
            rightMargin=MARGIN,
            topMargin=20 * mm,
            bottomMargin=18 * mm,
            title=title,
            author="Coinfidential Team",
            subject="Software Requirements Specification",
        )
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="main", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        self.addPageTemplates(
            [
                PageTemplate(id="cover", frames=[frame]),
                PageTemplate(id="content", frames=[frame], onPage=self._draw_page_furniture),
            ]
        )
        self._heading_number = 0

    def _draw_page_furniture(self, canvas, document) -> None:
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(GREY)
        canvas.drawString(MARGIN, A4[1] - 12 * mm, "Coinfidential: Software Requirements Specification")
        canvas.drawRightString(A4[0] - MARGIN, 10 * mm, f"Page {document.page}")
        canvas.setStrokeColor(RULE)
        canvas.setLineWidth(0.5)
        canvas.line(MARGIN, A4[1] - 14 * mm, A4[0] - MARGIN, A4[1] - 14 * mm)
        canvas.restoreState()

    def afterFlowable(self, flowable) -> None:
        if not isinstance(flowable, Paragraph):
            return
        levels = {"H2": 0, "H3": 1}
        level = levels.get(flowable.style.name)
        if level is None:
            return
        text = flowable.getPlainText()
        key = f"heading-{self._heading_number}"
        self._heading_number += 1
        self.canv.bookmarkPage(key)
        self.canv.addOutlineEntry(text, key, level=level, closed=level > 0)
        self.notify("TOCEntry", (level, text, self.page, key))

    def beforeDocument(self) -> None:
        self._heading_number = 0


def build_body(lines: list[str]) -> tuple[str, list, list]:
    """Return the title, the blocks before the first section, and the sections."""
    title = "Software Requirements Specification"
    front_matter: list = []
    sections: list = []
    current = front_matter
    position = 0

    while position < len(lines):
        line = lines[position]
        stripped = line.strip()

        if not stripped:
            position += 1
            continue

        if stripped.startswith("```"):
            position += 1
            code_lines = []
            while position < len(lines) and not lines[position].strip().startswith("```"):
                code_lines.append(lines[position])
                position += 1
            position += 1
            current.append(build_code_block(code_lines))
            continue

        heading = HEADING.fullmatch(stripped)
        if heading:
            level = len(heading.group(1))
            text = heading.group(2)
            if level == 1:
                title = text
            else:
                if level == 2:
                    if current is sections and sections:
                        sections.append(PageBreak())
                    current = sections
                current.append(Paragraph(format_inline(text), STYLES[f"h{level}"]))
            position += 1
            continue

        if stripped.startswith("|") and position + 1 < len(lines) and TABLE_DIVIDER.fullmatch(lines[position + 1]):
            rows = [split_table_row(stripped)]
            position += 2
            while position < len(lines) and lines[position].strip().startswith("|"):
                rows.append(split_table_row(lines[position]))
                position += 1
            current.append(build_table(rows))
            continue

        if stripped in ("---", "***"):
            current.append(HRFlowable(width="100%", thickness=0.5, color=RULE, spaceBefore=6, spaceAfter=8))
            position += 1
            continue

        item = LIST_ITEM.fullmatch(line)
        if item:
            current.append(build_list_item(item.group(1), item.group(2), item.group(3)))
            position += 1
            if position >= len(lines) or not lines[position].strip():
                current.append(Spacer(1, 4))
            continue

        style = STYLES["cover"] if current is front_matter else STYLES["body"]
        current.append(Paragraph(format_inline(stripped), style))
        position += 1

    return title, front_matter, sections


def check_characters(markdown: str) -> None:
    """Stop on characters that the built-in PDF fonts cannot show."""
    for line_number, line in enumerate(markdown.splitlines(), start=1):
        try:
            line.encode("cp1252")
        except UnicodeEncodeError as error:
            raise ValueError(f"Line {line_number} has a character the PDF fonts cannot show: {line[error.start]!r}") from error


def build_pdf(input_path: Path = DEFAULT_INPUT, output_path: Path = DEFAULT_OUTPUT) -> Path:
    markdown = input_path.read_text(encoding="utf-8")
    check_characters(markdown)
    title, front_matter, sections = build_body(markdown.splitlines())

    contents = TableOfContents()
    contents.levelStyles = [STYLES["toc0"], STYLES["toc1"]]
    contents.dotsMinLevel = 0

    story = [
        Spacer(1, 45 * mm),
        Paragraph(format_inline(title), STYLES["title"]),
        HRFlowable(width="40%", thickness=1.5, color=BLUE, spaceBefore=4, spaceAfter=22),
        *front_matter,
        NextPageTemplate("content"),
        PageBreak(),
        Paragraph("Contents", STYLES["toc_title"]),
        contents,
        PageBreak(),
        *sections,
    ]
    document = SrsDocument(str(output_path), title)
    document.multiBuild(story)
    return output_path


def main() -> int:
    output = build_pdf()
    print(f"OK: wrote {output.name} ({output.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
