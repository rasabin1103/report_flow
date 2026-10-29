"""Create an explicitly fictional logo and a fully personalized report example."""

import base64
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PIL import Image, ImageDraw, ImageFont

from app.reporting.design import FONT_DIR
from app.services.reports import execute


def main():
    root = Path(__file__).resolve().parents[1]
    folder = root / "examples"
    image = Image.new("RGBA", (900, 240), (255, 255, 255, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((10, 20, 200, 210), radius=32, fill="#167E91")
    draw.line([(55, 158), (55, 70), (151, 158), (151, 70)], fill="white", width=16, joint="curve")
    draw.text(
        (240, 30), "NORTE", font=ImageFont.truetype(str(FONT_DIR / "DejaVuSans-Bold.ttf"), 85), fill="#132B42"
    )
    draw.text(
        (245, 135),
        "EMPRESA DE DEMOSTRACIÓN",
        font=ImageFont.truetype(str(FONT_DIR / "DejaVuSans.ttf"), 27),
        fill="#536779",
    )
    logo = folder / "demo_logo.png"
    image.save(logo)
    config = json.loads((folder / "qa_config.json").read_text(encoding="utf-8"))
    config["report"].update(
        title="Calidad de producto y seguimiento de incidencias",
        subtitle="Informe de gestión · Primer semestre de 2026",
        author="Equipo de Calidad",
        prepared_for="Comité de Dirección",
        reporting_period="Enero – junio de 2026",
        document_reference="CAL-2026-S1 · Versión 1.0",
        confidentiality="Uso interno · Datos de demostración",
        cover_style="full",
    )
    config.setdefault("branding", {}).update(
        company_name="Norte · Empresa de demostración",
        accent_color="#167E91",
        footer_text="Norte | Informe de gestión · Uso interno",
        logo_base64=base64.b64encode(logo.read_bytes()).decode("ascii"),
    )
    raw = json.dumps(config, ensure_ascii=False, indent=2)
    (folder / "branded_config.json").write_text(raw, encoding="utf-8")
    result = execute("generate", (folder / "qa_incidents.csv").read_bytes(), "qa_incidents.csv", raw)
    (folder / "branded_report.pdf").write_bytes(result)
    print("branded report:", len(result), "bytes")


if __name__ == "__main__":
    main()
