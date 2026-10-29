"""Generate deterministic synthetic fixtures and actual reports; no external data."""

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd

from app.services.reports import execute


def main():
    root = Path(__file__).resolve().parents[1]
    examples = root / "examples"
    examples.mkdir(exist_ok=True)
    rng = random.Random(20261028)
    qa = pd.DataFrame(
        [
            {
                "proyecto": rng.choices(["Atlas", "Boreal", "Córdoba"], weights=[5, 3, 2])[0],
                "estado": rng.choices(["Abierta", "Resuelta", "En curso", "Cancelada"], weights=[3, 4, 2, 1])[
                    0
                ],
                "prioridad": rng.choices(["Crítica", "Alta", "Media", "Baja"], weights=[1, 3, 4, 2])[0],
                "fecha_creacion": str(pd.Timestamp("2026-01-01") + pd.Timedelta(days=rng.randrange(181)))[
                    :10
                ],
                "horas": None if i % 17 == 0 else round(rng.uniform(1, 24), 1),
            }
            for i in range(540)
        ]
    )
    sales = pd.DataFrame(
        [
            {
                "region": rng.choices(["North", "South", "West"], weights=[5, 3, 2])[0],
                "product": rng.choices(["Platform", "Support", "Training"], weights=[4, 4, 2])[0],
                "date": str(pd.Timestamp("2026-01-01") + pd.Timedelta(days=i % 180))[:10],
                "revenue": round(rng.uniform(600, 4100) * (1 + (i % 180) / 500), 2),
            }
            for i in range(540)
        ]
    )
    projects = pd.DataFrame(
        [
            {
                "project": f"Project {i + 1:03}",
                "status": "Delivered" if i % 5 == 0 else "At risk" if i % 7 == 0 else "On track",
                "team": rng.choice(["Engineering", "Operations", "Data"]),
                "progress": 100 if i % 5 == 0 else rng.randrange(15, 96),
            }
            for i in range(90)
        ]
    )
    qa.to_csv(examples / "qa_incidents.csv", index=False)
    sales.to_excel(examples / "sales.xlsx", index=False, sheet_name="Sales")
    projects.to_csv(examples / "projects.csv", index=False)
    qa_config = {
        "schema_version": "1.0",
        "report": {
            "title": "Informe ejecutivo de calidad",
            "subtitle": "Análisis de incidencias | Datos de demostración",
            "language": "es",
            "author": "Arce Sabin Engineering",
        },
        "dataset": {
            "columns": [
                {"source": c, "label": label, "type": kind}
                for c, label, kind in [
                    ("proyecto", "Proyecto", "string"),
                    ("estado", "Estado", "string"),
                    ("prioridad", "Prioridad", "string"),
                    ("fecha_creacion", "Fecha de creación", "date"),
                    ("horas", "Horas", "number"),
                ]
            ]
        },
        "filters": [{"column": "estado", "operator": "not_equals", "value": "Cancelada"}],
        "kpis": [
            {"id": "total", "label": "Total de incidencias", "operation": "count_rows"},
            {
                "id": "critical",
                "label": "Incidencias críticas",
                "operation": "count_rows",
                "filters": [{"column": "prioridad", "operator": "equals", "value": "Crítica"}],
            },
            {"id": "hours", "label": "Horas registradas", "operation": "sum", "column": "horas", "unit": "h"},
        ],
        "charts": [
            {"id": "projects", "title": "Incidencias por proyecto", "type": "bar", "group_by": "proyecto"},
            {
                "id": "priority",
                "title": "Distribución por prioridad",
                "type": "donut",
                "group_by": "prioridad",
            },
            {
                "id": "time",
                "title": "Evolución mensual",
                "type": "line",
                "group_by": "fecha_creacion",
                "time_granularity": "month",
            },
        ],
        "tables": [
            {
                "id": "project_status",
                "title": "Incidencias por proyecto y estado",
                "group_by": ["proyecto", "estado"],
                "aggregation": "count_rows",
                "columns": ["proyecto", "estado", "value"],
                "max_rows": 30,
                "include_total": True,
            }
        ],
    }
    sales_config = {
        "report": {
            "title": "Sales performance",
            "subtitle": "Revenue review | Synthetic demonstration data",
            "template": "detailed",
            "include_table_of_contents": False,
        },
        "kpis": [
            {"id": "count", "label": "Transactions", "operation": "count_rows"},
            {
                "id": "revenue",
                "label": "Revenue",
                "operation": "sum",
                "column": "revenue",
                "unit": "EUR",
                "comparison": 1000000,
            },
            {
                "id": "average",
                "label": "Average transaction",
                "operation": "average",
                "column": "revenue",
                "unit": "EUR",
            },
        ],
        "dataset": {
            "columns": [
                {"source": c, "label": label}
                for c, label in [
                    ("region", "Region"),
                    ("product", "Product"),
                    ("date", "Date"),
                    ("revenue", "Revenue"),
                ]
            ]
        },
        "charts": [
            {
                "id": "regions",
                "unit": "EUR",
                "title": "Revenue by region",
                "type": "horizontal_bar",
                "group_by": "region",
                "aggregation": "sum",
                "column": "revenue",
            },
            {
                "id": "trend",
                "unit": "EUR",
                "title": "Monthly revenue",
                "type": "line",
                "group_by": "date",
                "time_granularity": "month",
                "aggregation": "sum",
                "column": "revenue",
            },
        ],
        "tables": [
            {
                "id": "regional_table",
                "title": "Revenue by region",
                "group_by": "region",
                "aggregation": "sum",
                "column": "revenue",
                "columns": ["region", "value"],
                "include_total": True,
            },
            {
                "id": "products",
                "title": "Revenue by product",
                "group_by": "product",
                "aggregation": "sum",
                "column": "revenue",
                "columns": ["product", "value"],
                "include_total": True,
            },
        ],
    }
    project_config = {
        "report": {
            "title": "Project delivery status",
            "subtitle": "Portfolio review | Synthetic demonstration data",
            "orientation": "portrait",
        },
        "kpis": [
            {"id": "count", "label": "Projects", "operation": "count_rows"},
            {
                "id": "progress",
                "label": "Mean completion",
                "operation": "average",
                "column": "progress",
                "unit": "%",
            },
        ],
        "dataset": {
            "columns": [
                {"source": c, "label": label}
                for c, label in [
                    ("project", "Project"),
                    ("team", "Team"),
                    ("status", "Status"),
                    ("progress", "Completion (%)"),
                ]
            ]
        },
        "charts": [{"id": "status", "title": "Projects by status", "type": "pie", "group_by": "status"}],
        "tables": [
            {
                "id": "team_status",
                "title": "Projects by team and status",
                "group_by": ["team", "status"],
                "columns": ["team", "status", "value"],
                "include_total": True,
                "max_rows": 30,
            },
            {
                "id": "completion",
                "title": "Mean completion by team (%)",
                "group_by": "team",
                "aggregation": "average",
                "column": "progress",
                "columns": ["team", "value"],
            },
        ],
    }
    for source, config, stem in [
        ("qa_incidents.csv", qa_config, "qa"),
        ("sales.xlsx", sales_config, "sales"),
        ("projects.csv", project_config, "projects"),
    ]:
        raw = json.dumps(config, ensure_ascii=False, indent=2)
        (examples / f"{stem}_config.json").write_text(raw, encoding="utf-8")
        result = execute("generate", (examples / source).read_bytes(), source, raw)
        (examples / f"{stem}_report.pdf").write_bytes(result)
        print(stem, len(result), "bytes")
    (examples / "report_config.json").write_text(
        json.dumps(qa_config, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    fixtures = root / "tests" / "fixtures"
    fixtures.mkdir(parents=True, exist_ok=True)
    qa.to_csv(fixtures / "incidents_540.csv", index=False)


if __name__ == "__main__":
    main()
