import math
from typing import Any

import pandas as pd

from app.core.settings import ReportError
from app.ingestion.loader import column_type
from app.schemas.config import Config, Filter

NUMERIC = {"sum", "average"}


def require(frame: pd.DataFrame, column: str | None) -> str:
    if column is None or column not in frame.columns:
        raise ReportError(f"Missing or unavailable column: {column}")
    return column


def scalar(value: Any, series: pd.Series):
    kind = column_type(series)
    if value is None:
        raise ReportError("Use is_null or is_not_null for null comparisons")
    if kind == "number":
        if isinstance(value, bool):
            raise ReportError("Numeric filter requires a finite number")
        try:
            result = float(value)
            if not math.isfinite(result):
                raise ValueError
            return result
        except (TypeError, ValueError):
            raise ReportError("Numeric filter requires a finite number") from None
    if kind == "date":
        try:
            return pd.to_datetime(value, utc=True, errors="raise")
        except (ValueError, TypeError, OverflowError):
            raise ReportError("Date filter requires an ISO date") from None
    if kind == "boolean" and not isinstance(value, bool):
        raise ReportError("Boolean filter requires true or false")
    if kind == "string" and not isinstance(value, str):
        raise ReportError("Text filter requires a string")
    return value


def apply_filters(frame: pd.DataFrame, filters: list[Filter]) -> pd.DataFrame:
    result = frame
    for rule in filters:
        s = result[require(result, rule.column)]
        op = rule.operator
        if op in {"is_null", "is_not_null"}:
            mask = s.isna() if op == "is_null" else s.notna()
        elif op in {"in", "not_in", "between"}:
            if not isinstance(rule.value, list) or not rule.value or len(rule.value) > 1000:
                raise ReportError(
                    "Membership and range filters require a nonempty list of at most 1000 values"
                )
            values = [scalar(v, s) for v in rule.value]
            if op == "between":
                if len(values) != 2 or values[0] > values[1] or column_type(s) not in {"number", "date"}:
                    raise ReportError("between requires two ordered numeric or date bounds")
                mask = s.between(*values)
            else:
                mask = s.isin(values)
                if op == "not_in":
                    mask = ~mask
            mask &= s.notna()
        else:
            value = scalar(rule.value, s)
            if op == "contains":
                if column_type(s) != "string":
                    raise ReportError("contains requires a text column")
                mask = s.astype("string").str.contains(value, regex=False, na=False)
            else:
                if op not in {"equals", "not_equals"} and column_type(s) not in {"number", "date"}:
                    raise ReportError("Ordered comparisons require numeric or date columns")
                mask = {
                    "equals": s.eq,
                    "not_equals": s.ne,
                    "greater_than": s.gt,
                    "greater_or_equal": s.ge,
                    "less_than": s.lt,
                    "less_or_equal": s.le,
                }[op](value)
                mask &= s.notna()
        result = result.loc[mask.fillna(False)]
    return result


def validate_metric(frame: pd.DataFrame, operation: str, column: str | None):
    if operation == "count_rows":
        if column is not None:
            require(frame, column)
        return
    col = require(frame, column)
    kind = column_type(frame[col])
    if operation in NUMERIC and kind != "number":
        raise ReportError(f"{operation} requires a numeric column")
    if operation in {"minimum", "maximum"} and kind not in {"number", "date"}:
        raise ReportError(f"{operation} requires a numeric or date column")


def prepare(frame: pd.DataFrame, config: Config) -> tuple[pd.DataFrame, dict[str, str]]:
    frame = frame.copy()
    labels: dict[str, str] = {str(c): str(c) for c in frame}
    if config.dataset.columns:
        selected = [c for c in config.dataset.columns if c.include]
        if not selected:
            raise ReportError("At least one column must be selected")
        for col in config.dataset.columns:
            require(frame, col.source)
        frame = frame[[c.source for c in selected]].copy()
        for col in selected:
            s = frame[col.source]
            try:
                if col.type in {"number", "integer"}:
                    if column_type(s) == "boolean":
                        raise ValueError
                    converted = pd.to_numeric(s, errors="raise")
                    if col.type == "integer" and (converted.dropna() % 1 != 0).any():
                        raise ValueError
                    frame[col.source] = converted
                elif col.type == "date":
                    frame[col.source] = pd.to_datetime(s, errors="raise", utc=True, format="mixed")
                elif col.type == "boolean" and column_type(s) != "boolean":
                    raise ValueError
                elif col.type == "string":
                    frame[col.source] = s.astype("string")
            except (ValueError, TypeError, OverflowError):
                raise ReportError(
                    f"Column {col.source} is incompatible with declared type {col.type}"
                ) from None
            labels[col.source] = col.label or col.source
    result = apply_filters(frame, config.filters)
    for kpi in config.kpis:
        validate_metric(frame, kpi.operation, kpi.column)
        apply_filters(result, kpi.filters)
        if kpi.comparison is not None and kpi.column and column_type(frame[kpi.column]) == "date":
            raise ReportError("KPI baseline comparisons require numeric results")
    for chart in config.charts:
        groups = [chart.group_by] if isinstance(chart.group_by, str) else chart.group_by
        if not groups or len(groups) > 4 or len(set(groups)) != len(groups):
            raise ReportError("Grouping requires one to four distinct columns")
        for c in groups:
            require(frame, c)
        if "value" in groups:
            raise ReportError("Grouped column name value is reserved")
        validate_metric(frame, chart.aggregation, chart.column)
        if chart.time_granularity and (len(groups) != 1 or column_type(frame[groups[0]]) != "date"):
            raise ReportError("Time grouping requires a single date column")
    for table in config.tables:
        if table.include_total and (
            not table.group_by
            or table.aggregation not in {"count_rows", "count_non_null", "sum"}
            or "value" not in table.columns
            or table.columns[0] == "value"
        ):
            raise ReportError(
                "Table totals require additive grouped metrics, a leading group column and the value column"
            )
        if table.group_by:
            groups = [table.group_by] if isinstance(table.group_by, str) else table.group_by
            if not groups or len(groups) > 4 or len(set(groups)) != len(groups):
                raise ReportError("Grouping requires one to four distinct columns")
            for c in groups:
                require(frame, c)
            validate_metric(frame, table.aggregation, table.column)
            if any(c not in [*groups, "value"] for c in table.columns):
                raise ReportError("Grouped table columns must be group names or value")
            if "value" in groups:
                raise ReportError("Grouped column name value is reserved")
        else:
            for c in table.columns:
                require(frame, c)
    return result, labels
