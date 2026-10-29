import pandas as pd

from app.schemas.config import Chart, Table


def aggregate(frame: pd.DataFrame, operation: str, column: str | None = None):
    if operation == "count_rows":
        return len(frame)
    s = frame[column]
    if operation == "count_non_null":
        return int(s.count())
    if operation == "distinct_count":
        return int(s.nunique())
    if not s.notna().any():
        return None
    if operation == "sum":
        return s.sum(min_count=1)
    if operation == "average":
        return s.mean()
    if operation == "minimum":
        return s.min()
    return s.max()


def grouped(frame: pd.DataFrame, spec: Chart | Table, missing_policy: str) -> pd.DataFrame:
    groups = [spec.group_by] if isinstance(spec.group_by, str) else list(spec.group_by or [])
    data = frame.copy()
    granularity = getattr(spec, "time_granularity", None)
    if granularity:
        frequency = {"day": "D", "week": "W-SUN", "month": "M", "quarter": "Q", "year": "Y"}[granularity]
        data[groups[0]] = data[groups[0]].dt.tz_localize(None).dt.to_period(frequency).dt.start_time
    rows = []
    for key, subset in data.groupby(groups, dropna=missing_policy == "exclude", observed=True, sort=True):
        keys = key if isinstance(key, tuple) else (key,)
        rows.append([*keys, aggregate(subset, spec.aggregation, spec.column)])
    result = pd.DataFrame(rows, columns=[*groups, "value"])
    if result.empty:
        return result
    # Sort time series chronologically; other charts and tables sort by metric.
    order_col = groups[0] if granularity else "value"
    result = result.sort_values(
        order_col, ascending=True if granularity else spec.sort == "ascending", kind="stable"
    )
    for c in groups:
        result[c] = result[c].map(lambda x: "Unknown" if pd.isna(x) else x)
    return result.reset_index(drop=True)
