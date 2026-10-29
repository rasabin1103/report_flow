"""Branded cover component with bounded, measured typography and safe image placement."""

import io
from html import escape

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Flowable, Paragraph

from app.core.settings import ReportError
from app.reporting.localization import TEXT, display
from app.schemas.config import Config


class CoverPage(Flowable):
    def __init__(
        self,
        width: float,
        height: float,
        config: Config,
        logo: bytes | None,
        timestamp: str,
        records: int,
        columns: int,
    ):
        super().__init__()
        self.width, self.height = width, height
        self.config, self.logo = config, logo
        self.timestamp, self.records, self.columns = timestamp, records, columns

    def draw(self):
        canvas = self.canv
        w, h = self.width, self.height
        config = self.config
        es = config.report.language == "es"
        tr = TEXT[config.report.language]
        navy = colors.HexColor(config.branding.primary_color)
        blue = colors.HexColor(config.branding.accent_color)
        muted = colors.HexColor("#526779")
        pad = 24

        def paragraph(text, x, top, width, font_size=10, color=navy, bold=False, max_height=None):
            while True:
                style = ParagraphStyle(
                    "Cover",
                    fontName="RF-Bold" if bold else "RF",
                    fontSize=font_size,
                    leading=font_size * 1.3,
                    textColor=color,
                )
                item = Paragraph(escape(text), style)
                _, height = item.wrap(width, h)
                if max_height is None or height <= max_height:
                    break
                if font_size <= 10:
                    raise ReportError(
                        "Cover text exceeds the available layout; shorten the title or subtitle"
                    )
                font_size -= 1
            item.drawOn(canvas, x, top - height)
            return height

        if self.logo:
            image = ImageReader(io.BytesIO(self.logo))
            iw, ih = image.getSize()
            scale = min(220 / iw, 78 / ih)
            canvas.drawImage(image, pad, h - 88, width=iw * scale, height=ih * scale, mask="auto")
            paragraph(
                config.branding.company_name, w * 0.55, h - 17, w * 0.45 - pad, 11, bold=True, max_height=55
            )
        else:
            paragraph(config.branding.company_name, pad, h - 24, w - pad * 2, 16, bold=True, max_height=55)
        band_top = h - 125
        title_size = 32 if h > 600 else 24
        measurement = Paragraph(
            escape(config.report.title),
            ParagraphStyle("Measure", fontName="RF-Bold", fontSize=title_size, leading=title_size * 1.3),
        )
        _, measured_title = measurement.wrap(w - pad * 2, h)
        subtitle_measure = Paragraph(
            escape(config.report.subtitle),
            ParagraphStyle("SubMeasure", fontName="RF", fontSize=11, leading=16),
        )
        _, measured_subtitle = subtitle_measure.wrap(w - pad * 2, h)
        band_height = (
            23 + 32 + measured_title + (measured_subtitle + 17 if config.report.subtitle else 0) + 28
        )
        band_height = min(band_height, band_top - h * 0.36)
        band_bottom = band_top - band_height
        canvas.setFillColor(colors.HexColor("#F0F5F9"))
        canvas.rect(0, band_bottom, w, band_height, stroke=0, fill=1)
        canvas.setFillColor(blue)
        canvas.rect(0, band_bottom, 4, band_height, stroke=0, fill=1)
        y = band_top - 23
        paragraph(
            "INFORME EJECUTIVO" if es else "EXECUTIVE REPORT",
            pad,
            y,
            w - pad * 2,
            8,
            blue,
            True,
        )
        y -= 32
        subtitle = Paragraph(
            escape(config.report.subtitle),
            ParagraphStyle("Sub", fontName="RF", fontSize=11, leading=16, textColor=muted),
        )
        _, subtitle_height = subtitle.wrap(w - pad * 2, h)
        budget = y - band_bottom - 28 - (subtitle_height + 17 if config.report.subtitle else 0)
        title_height = paragraph(config.report.title, pad, y, w - pad * 2, title_size, navy, True, budget)
        if config.report.subtitle:
            subtitle.drawOn(canvas, pad, y - title_height - 17 - subtitle_height)
        metadata = [(tr["author"], config.report.author)]
        if config.report.prepared_for:
            metadata.append(("Preparado para" if es else "Prepared for", config.report.prepared_for))
        if config.report.reporting_period:
            metadata.append(
                ("Periodo del informe" if es else "Reporting period", config.report.reporting_period)
            )
        if config.report.document_reference:
            metadata.append(("Referencia" if es else "Reference", config.report.document_reference))
        metadata.append((tr["generated"], self.timestamp))
        y = band_bottom - 22
        column_width = (w - pad * 2 - 22) / 2
        for start in range(0, len(metadata), 2):
            row_height = 0
            for offset, (label, value) in enumerate(metadata[start : start + 2]):
                x = pad + offset * (column_width + 22)
                paragraph(label.upper(), x, y, column_width, 7, muted, True)
                used = paragraph(value, x, y - 15, column_width, 9, max_height=48)
                row_height = max(row_height, used + 15)
            y -= row_height + 14
        stats = (
            f"{display(self.records, config.report.language)} {tr['records'].lower()}   /   "
            f"{self.columns} {tr['columns'].lower()}"
        )
        canvas.setStrokeColor(colors.HexColor("#DCE5EC"))
        canvas.line(pad, 35, w - pad, 35)
        paragraph(stats, pad, 25, w * 0.55, 8, muted)
        if config.report.confidentiality:
            paragraph(config.report.confidentiality, w * 0.60, 25, w * 0.40 - pad, 7, muted, max_height=25)
