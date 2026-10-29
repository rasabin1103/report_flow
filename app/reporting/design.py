"""Shared editorial styles and template tokens for the ReportLab renderer."""

from dataclasses import dataclass
from pathlib import Path

import matplotlib
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.styles import ParagraphStyle, StyleSheet1
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

FONT_DIR = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
pdfmetrics.registerFont(TTFont("RF", str(FONT_DIR / "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("RF-Bold", str(FONT_DIR / "DejaVuSans-Bold.ttf")))
pdfmetrics.registerFontFamily("RF", normal="RF", bold="RF-Bold", italic="RF", boldItalic="RF-Bold")


@dataclass(frozen=True)
class Template:
    body_size: float
    table_size: float
    row_padding: float
    chart_ratio: float


TEMPLATES = {"executive": Template(9, 7.5, 4, 2.9 / 8), "detailed": Template(9, 8, 5, 3.2 / 8)}


def make_styles(primary: str, accent: str, template: Template) -> StyleSheet1:
    sheet = StyleSheet1()
    navy, blue = colors.HexColor(primary), colors.HexColor(accent)
    muted = colors.HexColor("#526779")
    definitions = [
        ("Body", {"fontSize": template.body_size, "leading": 14, "spaceAfter": 5, "textColor": navy}),
        ("Small", {"fontSize": 7.5, "leading": 11, "textColor": muted}),
        ("Micro", {"fontSize": 6.8, "leading": 10, "textColor": muted}),
        ("Kicker", {"fontSize": 8, "leading": 12, "textColor": blue, "fontName": "RF-Bold", "spaceAfter": 5}),
        ("Hero", {"fontSize": 25, "leading": 31, "textColor": colors.white, "fontName": "RF-Bold"}),
        (
            "HeroSub",
            {"fontSize": 9, "leading": 14, "textColor": colors.HexColor("#D9E4EE"), "spaceBefore": 8},
        ),
        (
            "Section",
            {
                "fontSize": 14,
                "leading": 19,
                "textColor": navy,
                "fontName": "RF-Bold",
                "spaceBefore": 16,
                "spaceAfter": 9,
                "keepWithNext": True,
            },
        ),
        (
            "ChartTitle",
            {
                "fontSize": 11,
                "leading": 15,
                "textColor": navy,
                "fontName": "RF-Bold",
                "spaceAfter": 4,
                "keepWithNext": True,
            },
        ),
        ("Insight", {"fontSize": 8.5, "leading": 13, "textColor": navy}),
        ("Cell", {"fontSize": template.table_size, "leading": 11, "textColor": navy, "splitLongWords": True}),
        (
            "Numeric",
            {"fontSize": template.table_size, "leading": 11, "textColor": navy, "alignment": TA_RIGHT},
        ),
        ("TableHeader", {"fontSize": 7, "leading": 10, "textColor": colors.white, "fontName": "RF-Bold"}),
        ("MethodLabel", {"fontSize": 7, "leading": 10, "textColor": muted, "fontName": "RF-Bold"}),
    ]
    for name, options in definitions:
        defaults = {"fontName": "RF", "allowWidows": 0, "allowOrphans": 0}
        defaults.update(options)
        sheet.add(ParagraphStyle(name, **defaults))
    return sheet
