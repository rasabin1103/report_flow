import base64
import io
import json
import multiprocessing
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook
from pypdf import PdfReader
from typer.testing import CliRunner

from app.analytics.metrics import aggregate, grouped
from app.core.settings import ReportError, Settings
from app.ingestion.loader import load
from app.main import app
from app.schemas.config import Chart, Dataset, Filter
from app.security import decode_logo
from app.services.reports import execute, parse_config
from app.services.worker import run_job
from app.transformations.engine import apply_filters
from cli.main import app as cli

DATA = (
    b"name,amount,date,active\nAlpha,10,2026-01-01,true\nBeta,20,2026-01-08,false\nAlpha,,2026-02-01,true\n"
)


def test_inspection_and_types():
    result = execute("inspect", DATA, "data.csv")
    assert result["total_rows"] == 3
    assert [c["type"] for c in result["columns"]] == ["string", "number", "date", "boolean"]
    assert result["columns"][1]["null_count"] == 1
    assert len(result["sample"]) == 3


def test_xlsx_formula_cache_and_sheet():
    book = Workbook()
    sheet = book.active
    sheet.title = "Data"
    sheet.append(["name", "amount"])
    sheet.append(["Alpha", "=1+1"])
    out = io.BytesIO()
    book.save(out)
    result = execute("inspect", out.getvalue(), "file.xlsx", options={"sheet_name": "Data"})
    assert result["sample"][0]["amount"] is None
    assert result["warnings"]
    with pytest.raises(ReportError, match="worksheet"):
        load(out.getvalue(), "file.xlsx", Dataset(sheet_name="Missing"), Settings())


@pytest.mark.parametrize(
    "data,name",
    [
        (b"a,a\n1,2", "a.csv"),
        (b"a,b\n1,2,3", "a.csv"),
        (b'a,b\n"broken,2', "a.csv"),
        (b"corrupt", "a.xlsx"),
        (b"a\n1", "a.xls"),
        (b"", "a.csv"),
    ],
)
def test_invalid_uploads(data, name):
    with pytest.raises(ReportError):
        execute("inspect", data, name)


@pytest.mark.parametrize(
    "settings",
    [
        Settings(max_file_bytes=5),
        Settings(max_rows=2),
        Settings(max_columns=2),
        Settings(max_rows=1),
    ],
)
def test_limits(settings):
    with pytest.raises(ReportError):
        execute("inspect", DATA, "a.csv", settings=settings)


def test_delimiters_and_encoding():
    result = execute(
        "inspect", "región;valor\nEspaña;12".encode("cp1252"), "a.csv", options={"encoding": "cp1252"}
    )
    assert result["column_names"] == ["región", "valor"]


@pytest.mark.parametrize(
    "operator,value,count",
    [
        ("equals", 10, 1),
        ("not_equals", 10, 1),
        ("greater_than", 10, 1),
        ("greater_or_equal", 10, 2),
        ("less_than", 20, 1),
        ("less_or_equal", 20, 2),
        ("in", [10], 1),
        ("not_in", [10], 1),
        ("between", [10, 20], 2),
        ("is_null", None, 1),
        ("is_not_null", None, 2),
    ],
)
def test_numeric_filters(operator, value, count):
    frame = load(DATA, "a.csv", Dataset(), Settings()).frame
    assert len(apply_filters(frame, [Filter(column="amount", operator=operator, value=value)])) == count


def test_contains_and_invalid_filters():
    frame = load(DATA, "a.csv", Dataset(), Settings()).frame
    assert len(apply_filters(frame, [Filter(column="name", operator="contains", value="Al")])) == 2
    for rule in [
        Filter(column="amount", operator="contains", value="1"),
        Filter(column="name", operator="greater_than", value="A"),
        Filter(column="amount", operator="between", value=[20, 10]),
        Filter(column="amount", operator="equals", value="bad"),
        Filter(column="missing", operator="is_null"),
    ]:
        with pytest.raises(ReportError):
            apply_filters(frame, [rule])


def test_config_and_column_validation():
    for raw in ['{"unknown":true}', '{"schema_version":"2.0"}', '{"charts":[{"id":"a"}]}']:
        with pytest.raises(ReportError):
            parse_config(raw)
    for config in [
        {"dataset": {"columns": [{"source": "missing"}]}},
        {"dataset": {"columns": [{"source": "name", "type": "number"}]}},
        {
            "dataset": {"columns": [{"source": "name"}]},
            "tables": [{"id": "a", "title": "a", "columns": ["amount"]}],
        },
        {"kpis": [{"id": "a", "label": "a", "operation": "sum", "column": "name"}]},
    ]:
        with pytest.raises(ReportError):
            execute("validate", DATA, "a.csv", json.dumps(config))


@pytest.mark.parametrize(
    "operation,value",
    [
        ("count_rows", 3),
        ("count_non_null", 2),
        ("sum", 30),
        ("average", 15),
        ("minimum", 10),
        ("maximum", 20),
        ("distinct_count", 2),
    ],
)
def test_aggregations(operation, value):
    frame = load(DATA, "a.csv", Dataset(), Settings()).frame
    assert aggregate(frame, operation, "amount") == value
    assert aggregate(frame.iloc[0:0], "sum", "amount") is None


@pytest.mark.parametrize("granularity", ["day", "week", "month", "quarter", "year"])
def test_date_grouping(granularity):
    frame = load(DATA, "a.csv", Dataset(), Settings()).frame
    spec = Chart(id="a", title="Date", type="line", group_by="date", time_granularity=granularity)
    data = grouped(frame, spec, "unknown")
    assert data["value"].sum() == 3
    if granularity == "week":
        assert all(d.weekday() == 0 for d in data["date"])


def test_null_groups_and_multiple_groups():
    frame = pd.DataFrame({"a": ["x", None, "x"], "b": ["y", "y", "z"], "v": [None, None, None]})
    spec = Chart(id="a", title="a", type="bar", group_by=["a", "b"])
    assert grouped(frame, spec, "unknown")["value"].sum() == 3
    assert grouped(frame, spec, "exclude")["value"].sum() == 2


@pytest.mark.parametrize("chart_type", ["bar", "horizontal_bar", "line", "pie", "donut"])
def test_chart_generation(chart_type):
    from app.charts.renderer import render_chart

    spec = Chart(id="a", title="Distribución", type=chart_type, group_by="name")
    result = render_chart(pd.DataFrame({"name": ["A", "B"], "value": [2, 3]}), spec, "#1A8FE3", {})
    assert result.startswith(b"\x89PNG")


def test_pdf_pagination_and_contents():
    data = Path("tests/fixtures/incidents_540.csv").read_bytes()
    config = {
        "report": {"title": "Pagination test", "include_cover": False},
        "kpis": [{"id": "total", "label": "Total records", "operation": "count_rows"}],
        "tables": [
            {
                "id": "t",
                "title": "Incident detail",
                "columns": ["proyecto", "estado", "prioridad", "fecha_creacion"],
                "max_rows": 500,
            }
        ],
    }
    result = execute("generate", data, "a.csv", json.dumps(config))
    assert result.startswith(b"%PDF-") and len(result) > 10000
    reader = PdfReader(io.BytesIO(result))
    assert len(reader.pages) >= 10
    text = "\n".join(p.extract_text() for p in reader.pages)
    for expected in ["Pagination test", "Total records", "540", "proyecto", "Rows omitted: 40"]:
        assert expected in text
    assert sum("proyecto" in p.extract_text() for p in reader.pages) >= 10
    with pytest.raises(ReportError, match="page limit"):
        execute("generate", data, "a.csv", json.dumps(config), settings=Settings(max_pages=1))


def test_logo_security():
    for encoded in ["https://evil.test/logo.png", base64.b64encode(b"bad").decode()]:
        with pytest.raises(ReportError):
            decode_logo(encoded)
    from PIL import Image

    stream = io.BytesIO()
    Image.new("RGB", (40, 20), "blue").save(stream, format="PNG")
    assert decode_logo(base64.b64encode(stream.getvalue()).decode()).startswith(b"\x89PNG")


def test_api():
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}
        assert "donut" in client.get("/api/v1/report-capabilities").json()["chart_types"]
        assert client.get("/api/v1/report-config-schema").status_code == 200
        for endpoint in ["datasets/inspect", "reports/validate", "reports/generate"]:
            response = client.post(
                "/api/v1/" + endpoint,
                files={"file": ("a.csv", DATA)},
                data={"config": '{"report":{"title":"API report"}}'},
            )
            assert response.status_code == 200, response.text[:200]
            if endpoint.endswith("generate"):
                assert response.content.startswith(b"%PDF-")
                assert "attachment" in response.headers["content-disposition"]
        response = client.post(
            "/api/v1/reports/validate",
            files={"file": ("a.csv", DATA)},
            data={"config": '{"unexpected":"secret"}'},
        )
        assert response.status_code == 422 and "secret" not in response.text


def test_cli(tmp_path):
    source = tmp_path / "data.csv"
    source.write_bytes(DATA)
    config = tmp_path / "config.json"
    config.write_text('{"report":{"title":"CLI report"}}')
    runner = CliRunner()
    for command in ["inspect", "validate", "generate"]:
        args = [command, "--input", str(source)]
        if command != "inspect":
            args += ["--config", str(config)]
        if command == "generate":
            args += ["--output", str(tmp_path / "report.pdf")]
        result = runner.invoke(cli, args)
        assert result.exit_code == 0, result.output
    assert (tmp_path / "report.pdf").read_bytes().startswith(b"%PDF-")


def test_timeout_and_cleanup(tmp_path, monkeypatch):
    monkeypatch.setenv("TEMP", str(tmp_path))
    before = set(tmp_path.iterdir())
    with pytest.raises(ReportError, match="time limit"):
        run_job("inspect", DATA, "a.csv", settings=Settings(timeout_seconds=0))
    assert not multiprocessing.active_children()
    assert set(tmp_path.iterdir()) == before


def test_no_dataset_persistence(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    execute("inspect", DATA, "a.csv")
    assert list(tmp_path.iterdir()) == []


def test_exact_cover_page_count():
    result = execute("generate", DATA, "a.csv", '{"report":{"title":"Cover only"},"sections":["cover"]}')
    reader = PdfReader(io.BytesIO(result))
    assert len(reader.pages) == 1
    assert "Cover only" in reader.pages[0].extract_text()


def test_invalid_chart_and_kpi_compatibility():
    for spec in [
        {
            "charts": [
                {"id": "a", "title": "a", "type": "bar", "group_by": "name", "time_granularity": "month"}
            ]
        },
        {"kpis": [{"id": "a", "label": "a", "operation": "minimum", "column": "date", "comparison": 2}]},
        {
            "charts": [
                {
                    "id": "a",
                    "title": "a",
                    "type": "pie",
                    "group_by": "name",
                    "aggregation": "sum",
                    "column": "amount",
                }
            ]
        },
    ]:
        data = DATA.replace(b"Alpha,10", b"Alpha,-10")
        with pytest.raises(ReportError):
            execute("validate", data, "a.csv", json.dumps(spec))


def test_xlsx_expansion_limit():
    book = Workbook()
    book.active.append(["a"])
    book.active.append([1])
    stream = io.BytesIO()
    book.save(stream)
    with pytest.raises(ReportError, match="expansion"):
        execute("inspect", stream.getvalue(), "a.xlsx", settings=Settings(max_uncompressed_bytes=10))


def test_bounded_samples_and_cell_length():
    result = execute("inspect", b"a\n" + b"x\n" * 100, "a.csv")
    assert len(result["sample"]) == 5
    with pytest.raises(ReportError, match="Cell text"):
        execute("inspect", b"a\n" + b"x" * 2001, "a.csv")


def test_empty_result_pdf_and_grouped_table():
    config = {
        "filters": [{"column": "amount", "operator": "greater_than", "value": 100}],
        "charts": [{"id": "chart", "title": "Empty", "type": "bar", "group_by": "name"}],
        "tables": [{"id": "table", "title": "Grouped", "columns": ["name", "value"], "group_by": "name"}],
    }
    assert execute("generate", DATA, "a.csv", json.dumps(config)).startswith(b"%PDF-")


def test_repeated_jobs_leave_no_children():
    before = {p.pid for p in multiprocessing.active_children()}
    assert run_job("validate", DATA, "a.csv", "{}")["valid"] is True
    with pytest.raises(ReportError):
        run_job("inspect", b"broken", "a.xlsx")
    assert {p.pid for p in multiprocessing.active_children()} == before


def test_api_size_limit_and_upload_closure(monkeypatch):
    from starlette.datastructures import UploadFile

    import app.main as module

    closed = []
    original = UploadFile.close

    async def track_close(self):
        closed.append(self.filename)
        await original(self)

    monkeypatch.setattr(UploadFile, "close", track_close)
    with TestClient(app) as client:
        response = client.post("/api/v1/datasets/inspect", files={"file": ("data.csv", DATA)})
        assert response.status_code == 200
        assert "data.csv" in closed
        monkeypatch.setattr(module.settings, "max_file_bytes", 10)
        response = client.post("/api/v1/datasets/inspect", files={"file": ("data.csv", DATA)})
        assert response.status_code == 413
        response = client.post(
            "/api/v1/datasets/inspect",
            content=b"x" * 1600011,
            headers={"Content-Type": "application/octet-stream"},
        )
        assert response.status_code == 413


def test_numpy_metric_number_formatting():
    import numpy as np

    from app.reporting.renderer import display

    assert display(np.int64(1449630)) == "1,449,630"
    assert display(np.float64(2684.5)) == "2,684.5"
