"""Ejecuta ASE ReportFlow para ASE (workflow_dispatch) o en local.

Usa directamente el motor del repo (sin servidor ni base de datos) y escribe:
  - report.html          informe autocontenido con el PDF incrustado (artefacto "pytest-report")
  - report.pdf           el PDF (artefacto "result-pdf")
  - request_result.json  resultado en bruto + bloque `ase_result` (artefacto "request-result")

Entradas por variables de entorno RF_* (las rellena el workflow):
  RF_DATASET      adjunto de ASE (gz64:<nombre>:<base64 gzip>), URL https o ruta del repo (.csv/.xlsx)
  RF_TITLE, RF_SUBTITLE, RF_LANGUAGE (es|en), RF_TEMPLATE (executive|detailed), RF_COVER (compact|full)
  RF_GROUP_BY, RF_METRIC, RF_OPERATION, RF_DATE_COLUMN   vacios = eleccion automatica
  RF_CONFIG       JSON de configuracion completo; si se indica, sustituye al automatico

Salida: 0 informe generado · 2 error.
Uso local (desde la raiz del repo):
  RF_DATASET=examples/qa_incidents.csv RF_TITLE="Calidad" python tools/ase_run.py
"""

from __future__ import annotations

import base64
import binascii
import gzip
import html
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.settings import ReportError, Settings  # noqa: E402
from app.services.reports import execute  # noqa: E402

SETTINGS = Settings()
MAX_BYTES = 2 * 1024 * 1024  # mismo tope que los adjuntos de ASE
MAX_GROUP_UNIQUE = 40
OPS = {"sum", "average", "minimum", "maximum", "distinct_count"}


def env(name: str) -> str:
    return (os.environ.get(name) or "").strip()


# --- informe -----------------------------------------------------------------

STYLE = (
    "body{font-family:system-ui,sans-serif;margin:1.2rem;color:#111}h1{font-size:1.2rem}"
    "a.btn{display:inline-block;margin:.4rem 0 .8rem;padding:.45rem .9rem;border-radius:.5rem;"
    "background:#1a8fe3;color:#fff;text-decoration:none;font-weight:600}"
    "iframe{width:100%;height:80vh;border:1px solid #ccc;border-radius:.5rem}pre{background:#f3f4f6;"
    "padding:.6rem;overflow:auto;font-size:.8rem}.muted{color:#6b7280}"
)


def write_outputs(title: str, data: dict, pdf: bytes | None = None, error: str = "") -> None:
    Path("request_result.json").write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    if pdf is not None:
        Path("report.pdf").write_bytes(pdf)
        uri = "data:application/pdf;base64," + base64.b64encode(pdf).decode("ascii")
        body = (
            f"<a class='btn' download='informe.pdf' href='{uri}'>Descargar PDF</a>"
            f"<iframe title='Informe' src='{uri}'></iframe>"
        )
    else:
        body = f"<p>{html.escape(error)}</p><pre>{html.escape(json.dumps(data, indent=2, ensure_ascii=False))}</pre>"
    Path("report.html").write_text(
        f"<!doctype html><html lang='es'><meta charset='utf-8'><title>{html.escape(title)}</title>"
        f"<style>{STYLE}</style><h1>{html.escape(title)}</h1>{body}",
        encoding="utf-8",
    )


HINTS = {
    "missing_input": "Adjunta un archivo .csv o .xlsx en la entrada 'dataset'.",
    "invalid_attachment": "Vuelve a adjuntar el archivo (.csv o .xlsx).",
    "download_failed": "Comprueba que la URL https es publica y accesible.",
    "invalid_source": "Usa un adjunto, una URL https o una ruta relativa del repo.",
    "file_not_found": "Revisa la ruta dentro del repo.",
    "upload_too_large": "Reduce el archivo (maximo 2 MiB).",
    "invalid_column": "Deja vacio el campo para que se elija solo, o usa un nombre de columna exacto.",
    "invalid_config": "Revisa el JSON de configuracion (esquema 1.0) o dejalo vacio.",
    "engine_error": "Revisa el formato, la codificacion y la cabecera del archivo.",
}


def ase_block(verdict, headline, explanation="", metrics=(), findings=(), inputs=()) -> dict:
    """Bloque legible que ASE muestra como tarjeta de resultado."""
    return {
        "tool": "ASE ReportFlow",
        "mode": "generate",
        "verdict": verdict,  # pass | warn | fail | error
        "headline": headline,
        "explanation": explanation,
        "metrics": [{"label": a, "value": str(b), "tone": c} for a, b, c in metrics],
        "findings": list(findings),
        "inputs": [{"label": a, "value": str(b)} for a, b in inputs],
        "truncated": False,
    }


def fail(message: str, code: str = "error") -> None:
    data = {
        "error": {"code": code, "message": message},
        "ase_result": ase_block(
            "error",
            "La ejecucion no se pudo completar",
            message,
            findings=[{"severity": "error", "title": code, "detail": message, "hint": HINTS.get(code, "")}],
        ),
    }
    write_outputs("ReportFlow · Error", data, error=message)
    print(f"ERROR [{code}]: {message}", file=sys.stderr)
    sys.exit(2)


# --- entrada -----------------------------------------------------------------


def load(source: str) -> tuple[str, bytes]:
    """Lee un adjunto de ASE (gz64:), una URL https o una ruta del repo (max 2 MiB)."""
    if not source:
        fail("Falta la entrada 'dataset'.", "missing_input")
    if source.startswith("gz64:"):
        try:
            _, quoted_name, packed = source.split(":", 2)
            data = gzip.decompress(base64.b64decode(packed))
        except (ValueError, OSError, binascii.Error):
            fail("El archivo adjunto no es valido.", "invalid_attachment")
        name = urllib.parse.unquote(quoted_name) or "dataset.csv"
    elif source.startswith("https://"):
        try:
            with urllib.request.urlopen(source, timeout=30) as resp:  # noqa: S310
                data = resp.read(MAX_BYTES + 1)
        except (urllib.error.URLError, TimeoutError) as exc:
            fail(f"No se pudo descargar el archivo: {exc}", "download_failed")
        name = source.rsplit("/", 1)[-1].split("?", 1)[0] or "dataset.csv"
    elif source.startswith(("http://", "file:", "/", "..")) or ".." in Path(source).parts:
        fail("'dataset' debe ser un adjunto, una URL https o una ruta relativa del repo.", "invalid_source")
    else:
        path = Path(source)
        if not path.is_file():
            fail(f"No existe el archivo {source} en el repo.", "file_not_found")
        data = path.read_bytes()[: MAX_BYTES + 1]
        name = path.name
    if len(data) > MAX_BYTES:
        fail(f"El archivo supera {MAX_BYTES // (1024 * 1024)} MiB.", "upload_too_large")
    return name, data


# --- configuracion automatica ------------------------------------------------

TEXT = {
    "es": {
        "total": "Total de registros",
        "chart_by": "Registros por {g}",
        "metric_by": "{op} de {m} por {g}",
        "trend": "Evolución mensual",
        "table": "Detalle por {g}",
        "ops": {"sum": "Suma", "average": "Media", "minimum": "Mínimo", "maximum": "Máximo",
                "distinct_count": "Valores distintos", "count_rows": "Registros"},
        "title": "Informe de datos",
    },
    "en": {
        "total": "Total records",
        "chart_by": "Records by {g}",
        "metric_by": "{op} of {m} by {g}",
        "trend": "Monthly trend",
        "table": "Breakdown by {g}",
        "ops": {"sum": "Sum", "average": "Average", "minimum": "Minimum", "maximum": "Maximum",
                "distinct_count": "Distinct values", "count_rows": "Records"},
        "title": "Data report",
    },
}


def pick(columns: list[dict], wanted: str, kinds: set[str], label: str, *, groupable: bool = False) -> str:
    """Columna pedida (validada) o la mejor candidata; '' si no hay."""
    names = {c["name"] for c in columns}
    if wanted:
        if wanted not in names:
            fail(f"{label}: la columna '{wanted}' no existe. Disponibles: {', '.join(sorted(names))}", "invalid_column")
        return wanted
    options = [c for c in columns if c["type"] in kinds]
    if groupable:
        options = [c for c in options if 2 <= c["unique_count"] <= MAX_GROUP_UNIQUE]
        options.sort(key=lambda c: c["unique_count"])
    return options[0]["name"] if options else ""


def build_config(info: dict) -> dict:
    lang = env("RF_LANGUAGE") if env("RF_LANGUAGE") in TEXT else "es"
    t = TEXT[lang]
    cols = info["columns"]
    group = pick(cols, env("RF_GROUP_BY"), {"string", "boolean"}, "group_by", groupable=True)
    metric = pick(cols, env("RF_METRIC"), {"number", "integer"}, "metric")
    date = pick(cols, env("RF_DATE_COLUMN"), {"date"}, "date_column")
    op = env("RF_OPERATION") if env("RF_OPERATION") in OPS else "sum"
    use_metric = bool(metric)
    agg = op if use_metric else "count_rows"
    extra = {"column": metric} if use_metric else {}

    kpis = [{"id": "total", "label": t["total"], "operation": "count_rows"}]
    if use_metric:
        kpis.append({"id": "metric", "label": f"{t['ops'][agg]} · {metric}", "operation": agg, "column": metric})
    charts, tables = [], []
    if group:
        title = t["metric_by"].format(op=t["ops"][agg], m=metric, g=group) if use_metric else t["chart_by"].format(g=group)
        charts.append({"id": "by_group", "title": title, "type": "bar", "group_by": group, "aggregation": agg, **extra})
        charts.append({"id": "share", "title": t["chart_by"].format(g=group), "type": "donut",
                       "group_by": group, "aggregation": "count_rows", "limit": 8})
        tables.append({"id": "group_table", "title": t["table"].format(g=group), "group_by": group,
                       "aggregation": agg, **extra, "columns": [group, "value"], "max_rows": 40,
                       "include_total": agg in {"count_rows", "sum"}})
    if date:
        charts.append({"id": "trend", "title": t["trend"], "type": "line", "group_by": date,
                       "aggregation": agg, **extra, "time_granularity": "month"})

    report = {"title": env("RF_TITLE") or t["title"], "language": lang,
              "template": env("RF_TEMPLATE") if env("RF_TEMPLATE") in {"executive", "detailed"} else "executive",
              "cover_style": env("RF_COVER") if env("RF_COVER") in {"compact", "full"} else "compact"}
    if env("RF_SUBTITLE"):
        report["subtitle"] = env("RF_SUBTITLE")
    dataset = {"sheet_name": info["selected_sheet"]} if len(info.get("sheet_names") or []) > 1 else {}
    return {"schema_version": "1.0", "report": report, "dataset": dataset, "kpis": kpis, "charts": charts, "tables": tables}


# --- ejecucion ---------------------------------------------------------------


def main() -> int:
    name, data = load(env("RF_DATASET"))
    if not name.lower().endswith((".csv", ".xlsx")):
        fail("Solo se admiten archivos .csv y .xlsx.", "invalid_attachment")
    try:
        info = execute("inspect", data, name, None, {}, SETTINGS)
        raw = env("RF_CONFIG")
        if raw:
            try:
                config = json.loads(raw)
            except ValueError:
                fail("RF_CONFIG no es un JSON valido.", "invalid_config")
        else:
            config = build_config(info)
        config_text = json.dumps(config)
        pdf = execute("generate", data, name, config_text, None, SETTINGS)
    except ReportError as exc:
        fail(str(exc), "engine_error")
    pdf = bytes(pdf)

    rep = config.get("report", {})
    warnings = list(info.get("warnings") or [])
    nulls = sum(c["null_count"] for c in info["columns"])
    findings = [{"severity": "warning", "title": w, "hint": ""} for w in warnings]
    if nulls:
        findings.append({"severity": "info", "title": f"{nulls} celdas vacías en los datos",
                         "hint": "Los vacíos no se cuentan como cero; el informe indica cómo se tratan."})
    verdict = "warn" if warnings else "pass"
    block = ase_block(
        verdict,
        "Informe PDF generado",
        "Gráficos y cifras calculados con todos los registros del archivo. Pulsa «Ver informe original» para ver o descargar el PDF.",
        metrics=[
            ("registros", info["total_rows"], "success"),
            ("columnas", info["total_columns"], ""),
            ("gráficos", len(config.get("charts", [])), ""),
            ("tamaño PDF (KB)", max(1, len(pdf) // 1024), ""),
        ],
        findings=findings,
        inputs=[("Archivo", name), ("Título", rep.get("title", "")), ("Idioma", rep.get("language", "")),
                ("Plantilla", rep.get("template", ""))],
    )
    write_outputs(
        f"ReportFlow · {rep.get('title', 'Informe')}",
        {"config": config, "dataset": {"file": name, "rows": info["total_rows"], "columns": info["column_names"]},
         "ase_result": block},
        pdf=pdf,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
