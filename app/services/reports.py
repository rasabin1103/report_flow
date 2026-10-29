import base64
import json

from pydantic import ValidationError

from app.analytics.metrics import grouped
from app.core.settings import ReportError, Settings
from app.ingestion.loader import inspect_dataset, load
from app.reporting.renderer import render
from app.schemas.config import Config, Dataset
from app.security import decode_logo
from app.transformations.engine import prepare

OPERATIONS = ["count_rows", "count_non_null", "sum", "average", "minimum", "maximum", "distinct_count"]
CAPABILITIES = {
    "schema_version": "1.0",
    "file_formats": ["csv", "xlsx"],
    "aggregations": OPERATIONS,
    "chart_types": ["bar", "horizontal_bar", "line", "pie", "donut"],
    "filter_operators": [
        "equals",
        "not_equals",
        "greater_than",
        "greater_or_equal",
        "less_than",
        "less_or_equal",
        "in",
        "not_in",
        "contains",
        "is_null",
        "is_not_null",
        "between",
    ],
    "pdf_templates": ["executive", "detailed"],
}


def parse_config(raw: str) -> Config:
    if len(raw.encode("utf-8")) > 1000000:
        raise ReportError("Configuration size limit exceeded", 413)
    try:
        return Config.model_validate_json(raw)
    except ValidationError as exc:
        fields = [".".join(map(str, e["loc"])) or "config" for e in exc.errors()]
        raise ReportError("Invalid configuration fields: " + ", ".join(fields[:15])) from None


def presentation_config(
    raw: str,
    *,
    title: str | None = None,
    subtitle: str | None = None,
    cover_style: str | None = None,
    logo: bytes | None = None,
) -> str:
    """Shared API/CLI overrides, validated by the same public schema as JSON input."""
    payload = parse_config(raw).model_dump()
    for key, value in {"title": title, "subtitle": subtitle, "cover_style": cover_style}.items():
        if value is not None:
            payload["report"][key] = value
    if logo is not None:
        if not logo:
            raise ReportError("Logo must not be empty")
        if len(logo) > 500000:
            raise ReportError("Logo size limit exceeded", 413)
        encoded = base64.b64encode(logo).decode("ascii")
        decode_logo(encoded)
        payload["branding"]["logo_base64"] = encoded
    return parse_config(json.dumps(payload)).model_dump_json()


def execute(
    action: str,
    data: bytes,
    filename: str,
    raw: str | None = None,
    options: dict | None = None,
    settings: Settings | None = None,
):
    settings = settings or Settings()
    config = parse_config(raw) if raw is not None else Config(dataset=Dataset(**(options or {})))
    loaded = load(data, filename, config.dataset, settings)
    if action == "inspect":
        return inspect_dataset(loaded)
    frame, labels = prepare(loaded.frame, config)
    logo = decode_logo(config.branding.logo_base64)
    for chart in config.charts:
        values = grouped(frame, chart, config.dataset.missing_policy)["value"]
        if chart.type in {"pie", "donut"} and (values.dropna() < 0).any():
            raise ReportError("Pie and donut charts require nonnegative values")
    if action == "validate":
        return {
            "valid": True,
            "records_loaded": len(loaded.frame),
            "records_analyzed": len(frame),
            "selected_columns": list(frame.columns),
            "warnings": loaded.warnings,
        }
    if action != "generate":
        raise ReportError("Unknown operation")
    return render(loaded, frame, labels, config, settings, logo)
