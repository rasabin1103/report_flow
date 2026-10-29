"""Editorial quality regressions: one finding per report and complete grouped evidence."""

import io
import json
from pathlib import Path

import pytest
from pypdf import PdfReader

from app.core.settings import ReportError
from app.services.reports import execute

DATA = b"group,amount\nA,5\nB,3\nC,2\n"


def pdf_text(result):
    return " ".join(" ".join(page.extract_text() for page in PdfReader(io.BytesIO(result)).pages).split())


def test_findings_are_not_repeated_below_charts():
    config = {"charts": [{"id": "a", "title": "Distribution", "type": "bar", "group_by": "group"}]}
    text = pdf_text(execute("generate", DATA, "data.csv", json.dumps(config)))
    assert text.count("All 3 categories have the same value") == 1
    config["report"] = {"include_executive_summary": False}
    text = pdf_text(execute("generate", DATA, "data.csv", json.dumps(config)))
    assert text.count("All 3 categories have the same value") == 1


def test_total_includes_omitted_groups_and_explains_it():
    config = {
        "tables": [
            {
                "id": "summary",
                "title": "Amounts",
                "group_by": "group",
                "aggregation": "sum",
                "column": "amount",
                "columns": ["group", "value"],
                "max_rows": 1,
                "include_total": True,
            }
        ]
    }
    text = pdf_text(execute("generate", DATA, "data.csv", json.dumps(config)))
    assert "TOTAL 10" in text
    assert "Rows omitted: 2" in text
    assert "total includes all groups" in text


@pytest.mark.parametrize(
    "changes",
    [
        {"aggregation": "average"},
        {"group_by": None},
        {"columns": ["value"]},
        {"aggregation": "distinct_count"},
    ],
)
def test_invalid_total_definitions_are_rejected(changes):
    table = {
        "id": "summary",
        "title": "Amounts",
        "group_by": "group",
        "aggregation": "sum",
        "column": "amount",
        "columns": ["group", "value"],
        "include_total": True,
    }
    table.update(changes)
    with pytest.raises(ReportError, match="totals require"):
        execute("validate", DATA, "data.csv", json.dumps({"tables": [table]}))


def test_all_null_sum_total_remains_missing():
    config = {
        "dataset": {"columns": [{"source": "group"}, {"source": "amount", "type": "number"}]},
        "tables": [
            {
                "id": "sum",
                "title": "Amounts",
                "group_by": "group",
                "aggregation": "sum",
                "column": "amount",
                "columns": ["group", "value"],
                "include_total": True,
            }
        ],
    }
    text = pdf_text(execute("generate", b"group,amount\nA,\nB,\n", "null.csv", json.dumps(config)))
    assert "TOTAL —" in text


def test_examples_use_complete_grouped_summaries_instead_of_row_samples():
    for stem in ["qa", "sales", "projects"]:
        config = json.loads(Path(f"examples/{stem}_config.json").read_text(encoding="utf-8"))
        assert all(table.get("group_by") for table in config["tables"])
        text = pdf_text(Path(f"examples/{stem}_report.pdf").read_bytes())
        assert ("Filas omitidas: 0" if stem == "qa" else "Rows omitted: 0") in text
        assert "TOTAL" in text
