"""Presentation overrides and logo transport must agree across the API and CLI."""

import base64
import io
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from pypdf import PdfReader
from typer.testing import CliRunner

from app.core.settings import ReportError
from app.main import app
from app.security import decode_logo
from app.services.reports import execute, presentation_config
from cli.main import app as cli


def logo_bytes():
    stream = io.BytesIO()
    image = Image.new("RGBA", (240, 80), (0, 120, 160, 0))
    image.putpixel((100, 40), (0, 120, 160, 255))
    image.save(stream, format="PNG")
    return stream.getvalue()


def test_logo_transparency_and_pixel_aspect_are_preserved():
    result = decode_logo(base64.b64encode(logo_bytes()).decode())
    with Image.open(io.BytesIO(result)) as image:
        assert image.mode == "RGBA" and image.size == (240, 80)
        assert image.getpixel((0, 0))[3] == 0
        assert image.getpixel((100, 40))[3] == 255
        assert "exif" not in image.info


@pytest.mark.parametrize(
    "overrides",
    [
        {"title": ""},
        {"title": "   "},
        {"title": "x" * 201},
        {"cover_style": "invalid"},
        {"logo": b""},
        {"logo": b"x" * 500001},
        {"logo": b"https://example.org/logo.png"},
    ],
)
def test_override_validation(overrides):
    with pytest.raises(ReportError):
        presentation_config("{}", **overrides)


def test_explicit_overrides_win_without_mutating_json():
    raw = '{"report":{"title":"Original"}}'
    result = json.loads(
        presentation_config(raw, title="Personalizado", logo=logo_bytes(), cover_style="full")
    )
    assert result["report"]["title"] == "Personalizado"
    assert base64.b64decode(result["branding"]["logo_base64"]) == logo_bytes()
    assert json.loads(raw)["report"]["title"] == "Original"


def test_full_cover_has_identity_metadata_logo_and_final_page_totals():
    config = {
        "report": {
            "title": "Informe personalizado",
            "language": "es",
            "cover_style": "full",
            "subtitle": "Revisión de operaciones",
            "prepared_for": "Dirección",
            "reporting_period": "2026-S1",
            "document_reference": "DOC-001",
            "confidentiality": "Confidencial",
        },
        "branding": {"logo_base64": base64.b64encode(logo_bytes()).decode()},
    }
    result = execute("generate", b"a\nx\ny\n", "data.csv", json.dumps(config))
    reader = PdfReader(io.BytesIO(result))
    first = reader.pages[0].extract_text()
    for text in [
        "Informe personalizado",
        "Revisión de operaciones",
        "Dirección",
        "2026-S1",
        "DOC-001",
        "Confidencial",
    ]:
        assert text in first
    assert len(reader.pages[0].images) > 0
    for number, page in enumerate(reader.pages, 1):
        assert f"Página {number:02} de {len(reader.pages):02}" in page.extract_text()


def test_multipart_logo_title_and_cleanup(monkeypatch):
    from starlette.datastructures import UploadFile

    closed = []
    close = UploadFile.close

    async def track(self):
        closed.append(self.filename)
        await close(self)

    monkeypatch.setattr(UploadFile, "close", track)
    with TestClient(app) as client:
        for endpoint in ["validate", "generate"]:
            response = client.post(
                f"/api/v1/reports/{endpoint}",
                files={
                    "file": ("data.csv", b"a\nx\ny\n", "text/csv"),
                    "logo": ("brand.png", logo_bytes(), "image/png"),
                },
                data={"config": "{}", "title": "API custom cover", "cover_style": "full"},
            )
            assert response.status_code == 200, response.text[:100]
            if endpoint == "generate":
                first = PdfReader(io.BytesIO(response.content)).pages[0]
                assert "API custom cover" in first.extract_text() and len(first.images) > 0
        response = client.post(
            "/api/v1/reports/generate",
            files={"file": ("data.csv", b"a\nx\n"), "logo": ("bad.png", b"invalid")},
            data={"config": "{}", "title": "Invalid image"},
        )
        assert response.status_code == 422
    assert "brand.png" in closed and "bad.png" in closed and "data.csv" in closed


def test_cli_can_customize_title_and_logo(tmp_path):
    source = tmp_path / "data.csv"
    source.write_bytes(b"a\nx\ny\n")
    config = tmp_path / "config.json"
    config.write_text("{}", encoding="utf-8")
    logo = tmp_path / "logo.png"
    logo.write_bytes(logo_bytes())
    output = tmp_path / "custom.pdf"
    args = [
        "--input",
        str(source),
        "--config",
        str(config),
        "--title",
        "CLI custom cover",
        "--subtitle",
        "Operational report",
        "--logo",
        str(logo),
        "--cover-style",
        "full",
    ]
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", *args])
    assert result.exit_code == 0, result.output
    result = runner.invoke(cli, ["generate", *args, "--output", str(output)])
    assert result.exit_code == 0, result.output
    reader = PdfReader(output)
    assert "CLI custom cover" in reader.pages[0].extract_text()
    assert len(reader.pages[0].images) > 0


def test_personalized_example_is_an_actual_generated_pdf():
    reader = PdfReader(Path("examples/branded_report.pdf"))
    assert len(reader.pages) == 4
    assert "Norte" in reader.pages[0].extract_text()
    assert len(reader.pages[0].images) > 0
