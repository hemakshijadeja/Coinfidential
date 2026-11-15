"""Diagrams for docs/SRS.md, drawn with ReportLab graphics.

The same drawings are embedded as vectors in the PDF and saved as SVG files in
docs/diagrams/, which GitHub shows inside SRS.md.
"""

from collections.abc import Callable

from reportlab.graphics.shapes import (
    Circle,
    Drawing,
    Ellipse,
    Line,
    Polygon,
    Rect,
    String,
)
from reportlab.lib import colors
from reportlab.pdfbase.pdfmetrics import stringWidth

NAVY = colors.HexColor("#1F3A5F")
BLUE = colors.HexColor("#1F5FA8")
GREY = colors.HexColor("#5A6472")
LIGHT = colors.HexColor("#EEF3F9")
RED = colors.HexColor("#B42318")
FONT = "Helvetica"
BOLD = "Helvetica-Bold"


def text(x: float, y: float, value: str, size: float = 8, font: str = FONT, color=NAVY, anchor: str = "middle") -> String:
    return String(x, y, value, fontName=font, fontSize=size, fillColor=color, textAnchor=anchor)


def actor(drawing: Drawing, x: float, y: float, label: str) -> None:
    """A stick figure whose feet stand at height y."""
    drawing.add(Circle(x, y + 50, 7, strokeColor=NAVY, fillColor=colors.white, strokeWidth=1.2))
    drawing.add(Line(x, y + 43, x, y + 20, strokeColor=NAVY, strokeWidth=1.2))
    drawing.add(Line(x - 13, y + 35, x + 13, y + 35, strokeColor=NAVY, strokeWidth=1.2))
    drawing.add(Line(x, y + 20, x - 10, y, strokeColor=NAVY, strokeWidth=1.2))
    drawing.add(Line(x, y + 20, x + 10, y, strokeColor=NAVY, strokeWidth=1.2))
    drawing.add(text(x, y - 12, label, size=8.5, font=BOLD))


def use_case_diagram() -> Drawing:
    width, height = 480, 270
    drawing = Drawing(width, height)
    drawing.add(Rect(130, 12, 220, 246, strokeColor=NAVY, fillColor=colors.white, strokeWidth=1.2))
    drawing.add(text(240, 244, "Coinfidential", size=9.5, font=BOLD))

    use_cases = [
        ("Create account and wallets", "FR-1", 212),
        ("Transfer money", "FR-2, FR-3", 170),
        ("View wallet and history", "FR-4", 128),
        ("Reverse a transfer", "FR-4", 86),
        ("Check the whole ledger", "FR-5", 44),
    ]
    rx, ry = 92, 17
    for name, ids, y in use_cases:
        drawing.add(Ellipse(240, y, rx, ry, strokeColor=BLUE, fillColor=LIGHT, strokeWidth=1))
        drawing.add(text(240, y + 1, name, size=8))
        drawing.add(text(240, y - 9, ids, size=6.5, color=GREY))

    holder_x, admin_x, actors_y = 55, 425, 100
    actor(drawing, holder_x, actors_y, "Wallet holder")
    actor(drawing, admin_x, actors_y, "Administrator")
    shoulder = actors_y + 35
    for _, _, y in use_cases[:4]:
        drawing.add(Line(holder_x + 14, shoulder, 240 - rx, y, strokeColor=GREY, strokeWidth=0.8))
    for _, _, y in use_cases[2:]:
        drawing.add(Line(admin_x - 14, shoulder, 240 + rx, y, strokeColor=GREY, strokeWidth=0.8))

    drawing.add(text(240, 1, "Every use case requires a valid access token.", size=7, color=GREY))
    return drawing


def arrow(drawing: Drawing, x1: float, x2: float, y: float, label: str, dashed: bool = False, lost: bool = False) -> None:
    """A message from x1 to x2 at height y, with its label above the line."""
    # A lost message stops at a cross three-quarters of the way, with its label before the cross.
    end = x1 + (x2 - x1) * 0.78 if lost else x2
    direction = 1 if x2 > x1 else -1
    drawing.add(
        Line(x1, y, end, y, strokeColor=RED if lost else NAVY, strokeWidth=1, strokeDashArray=[3, 2] if dashed else None)
    )
    if lost:
        drawing.add(Line(end - 4, y - 4, end + 4, y + 4, strokeColor=RED, strokeWidth=1.4))
        drawing.add(Line(end - 4, y + 4, end + 4, y - 4, strokeColor=RED, strokeWidth=1.4))
    else:
        drawing.add(
            Polygon(
                [end, y, end - 7 * direction, y + 3, end - 7 * direction, y - 3],
                fillColor=NAVY,
                strokeColor=NAVY,
                strokeWidth=0.5,
            )
        )
    span = abs(end - x1) - 12 if lost else abs(x2 - x1) - 8
    size = 7.3
    while stringWidth(label, FONT, size) > span and size > 6:
        size -= 0.2
    label_x = (x1 + end + 6 * direction) / 2 if lost else (x1 + x2) / 2
    drawing.add(text(label_x, y + 3.5, label, size=size, color=RED if lost else NAVY))


def sequence_diagram() -> Drawing:
    width, height = 480, 345
    drawing = Drawing(width, height)
    client, service, ledger = 70, 245, 415
    top, bottom = 318, 8

    for x, name in ((client, "Client"), (service, "Coinfidential service"), (ledger, "Ledger database")):
        box_width = stringWidth(name, BOLD, 8.5) + 18
        drawing.add(Rect(x - box_width / 2, top, box_width, 22, strokeColor=NAVY, fillColor=LIGHT, strokeWidth=1))
        drawing.add(text(x, top + 8, name, size=8.5, font=BOLD))
        drawing.add(Line(x, top, x, bottom, strokeColor=GREY, strokeWidth=0.7, strokeDashArray=[2, 2]))

    step = 21
    y = top - 18
    messages = [
        (client, service, "1. Transfer request with idempotency key K", False, False),
        (service, ledger, "2. Lock the ledger for writing", False, False),
        (service, ledger, "3. Has key K been used before?", False, False),
        (ledger, service, "4. No", True, False),
        (service, ledger, "5. Is the balance enough?", False, False),
        (ledger, service, "6. Yes", True, False),
        (service, ledger, "7. Save both entries, balances and K", False, False),
        (ledger, service, "8. All saved together", True, False),
        (service, client, "9. Confirmation lost (network error)", True, True),
    ]
    for x1, x2, label, dashed, lost in messages:
        arrow(drawing, x1, x2, y, label, dashed, lost)
        y -= step

    drawing.add(Rect(18, y - 4, width - 36, 14, strokeColor=None, fillColor=LIGHT))
    drawing.add(text(width / 2, y, "The client retries, because it never received a reply", size=7.5, font=BOLD, color=GREY))
    y -= step

    for x1, x2, label, dashed in [
        (client, service, "10. Same request, same key K", False),
        (service, ledger, "11. Has key K been used before?", False),
        (ledger, service, "12. Yes", True),
        (service, client, "13. Original confirmation; no money moves", True),
    ]:
        arrow(drawing, x1, x2, y, label, dashed)
        y -= step
    return drawing


DIAGRAMS: dict[str, Callable[[], Drawing]] = {
    "use-case": use_case_diagram,
    "transfer-sequence": sequence_diagram,
}
