"""Presentation vocabulary and number formatting, independent of the host locale."""

from datetime import datetime
from numbers import Integral, Real

import pandas as pd

TEXT = {
    "en": {
        "executive_summary": "Executive brief",
        "kpis": "Performance at a glance",
        "charts": "Analysis",
        "tables": "Data appendix",
        "methodology": "Scope & methodology",
        "contents": "Contents",
        "records": "Records",
        "columns": "Columns",
        "filters": "Filters",
        "generated": "Issued",
        "source": "Source",
        "worksheet": "Worksheet",
        "loaded": "Records loaded",
        "analyzed": "Records analyzed",
        "selected": "Selected columns",
        "none": "None",
        "unknown": "Unknown",
        "value": "Value",
        "baseline": "Baseline",
        "difference": "Difference",
        "findings": "Key observations",
        "quality": "Data coverage",
        "period": "Observed period",
        "no_data": "No records match the selected scope.",
        "no_values": "No non-null values to display.",
        "zero_values": "All displayed values are zero.",
        "author": "Prepared by",
        "missing_policy": "Missing categories",
        "aggregations": "Calculation methods",
        "footer": "Prepared with ASE ReportFlow",
        "page": "Page",
        "of": "of",
        "count_rows": "Record count",
        "count_non_null": "Non-null count",
        "sum": "Sum",
        "average": "Average",
        "minimum": "Minimum",
        "maximum": "Maximum",
        "distinct_count": "Distinct count",
        "equals": "equals",
        "not_equals": "does not equal",
        "greater_than": "is greater than",
        "greater_or_equal": "is at least",
        "less_than": "is less than",
        "less_or_equal": "is at most",
        "in": "is one of",
        "not_in": "is not one of",
        "contains": "contains",
        "is_null": "is missing",
        "is_not_null": "is present",
        "between": "is between",
    },
    "es": {
        "executive_summary": "Síntesis ejecutiva",
        "kpis": "Indicadores principales",
        "charts": "Análisis",
        "tables": "Anexo de datos",
        "methodology": "Alcance y metodología",
        "contents": "Contenido",
        "records": "Registros",
        "columns": "Columnas",
        "filters": "Filtros",
        "generated": "Emisión",
        "source": "Fuente",
        "worksheet": "Hoja",
        "loaded": "Registros cargados",
        "analyzed": "Registros analizados",
        "selected": "Columnas seleccionadas",
        "none": "Ninguno",
        "unknown": "Sin dato",
        "value": "Valor",
        "baseline": "Referencia",
        "difference": "Diferencia",
        "findings": "Observaciones clave",
        "quality": "Cobertura de datos",
        "period": "Periodo observado",
        "no_data": "Ningún registro coincide con el alcance seleccionado.",
        "no_values": "No hay valores disponibles para mostrar.",
        "zero_values": "Todos los valores mostrados son cero.",
        "author": "Elaborado por",
        "missing_policy": "Categorías sin dato",
        "aggregations": "Métodos de cálculo",
        "footer": "Elaborado con ASE ReportFlow",
        "page": "Página",
        "of": "de",
        "count_rows": "Recuento de registros",
        "count_non_null": "Recuento no nulo",
        "sum": "Suma",
        "average": "Media",
        "minimum": "Mínimo",
        "maximum": "Máximo",
        "distinct_count": "Valores distintos",
        "equals": "es igual a",
        "not_equals": "es distinto de",
        "greater_than": "es mayor que",
        "greater_or_equal": "es mayor o igual que",
        "less_than": "es menor que",
        "less_or_equal": "es menor o igual que",
        "in": "pertenece a",
        "not_in": "no pertenece a",
        "contains": "contiene",
        "is_null": "no tiene dato",
        "is_not_null": "tiene dato",
        "between": "está entre",
    },
}


def display(value, language: str = "en", decimals: int = 2) -> str:
    if value is None or pd.isna(value):
        return "—"
    if isinstance(value, (datetime, pd.Timestamp)):
        return value.strftime("%d/%m/%Y" if language == "es" else "%Y-%m-%d")
    if isinstance(value, bool):
        return ("Sí" if value else "No") if language == "es" else ("Yes" if value else "No")
    if isinstance(value, Real):
        result = (
            f"{value:,}"
            if isinstance(value, Integral)
            else (f"{value:,.{decimals}f}".rstrip("0").rstrip(".") if decimals else f"{value:,.0f}")
        )
        return result.translate(str.maketrans(",.", ".,")) if language == "es" else result
    return str(value)


def metric_label(operation: str, column: str | None, labels: dict[str, str], language: str) -> str:
    title = TEXT[language][operation]
    return f"{labels.get(column, column)} · {title.lower()}" if column else title
