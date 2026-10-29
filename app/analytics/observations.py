"""Descriptive statements with explicit denominators; no inferred causes or advice."""

import math

import pandas as pd

from app.reporting.localization import display
from app.schemas.config import Chart


def chart_observation(data: pd.DataFrame, spec: Chart, language: str = "en") -> str | None:
    """Use the complete grouping, before display limits, to avoid top-N bias."""
    spanish = language == "es"
    if data.empty:
        return None
    values = pd.to_numeric(data["value"], errors="coerce")
    valid = values.notna() & values.map(lambda v: math.isfinite(v) if pd.notna(v) else False)
    usable = data.loc[valid].copy()
    usable["value"] = values[valid]
    if usable.empty:
        return None
    if spec.time_granularity:
        groups = [c for c in data.columns if c != "value"]
        dates = pd.to_datetime(usable[groups[0]], errors="coerce", utc=True)
        dated = usable.loc[dates.notna()].copy()
        dated[groups[0]] = dates[dates.notna()]
        dated = dated.sort_values(groups[0])
        if len(dated) < 2:
            return None
        first, last = dated.iloc[0], dated.iloc[-1]
        start, end = float(first["value"]), float(last["value"])
        if start == 0 or not math.isfinite(start) or not math.isfinite(end):
            return None
        delta = (end - start) / abs(start) * 100
        if delta == 0:
            return (
                "El primer y el último intervalo observado registran el mismo valor."
                if spanish
                else "The first and last observed intervals have the same value."
            )
        suffix = f" {spec.unit}" if spec.unit else ""
        if spanish:
            return (
                f"Entre {display(first[groups[0]], language)} y {display(last[groups[0]], language)}, "
                f"{'el recuento' if spec.aggregation == 'count_rows' else 'el importe' if spec.unit else 'la medida'} "
                f"pasa de {display(start, language)} a {display(end, language)}{suffix}: "
                f"{display(abs(delta), language)} % {'más' if delta > 0 else 'menos'}. "
                "Comparación de intervalos observados; no implica periodos completos."
            )
        return (
            f"From {display(first[groups[0]], language)} to {display(last[groups[0]], language)}, "
            f"{'the record count' if spec.aggregation == 'count_rows' else 'the amount' if spec.unit else 'the measure'} "
            f"moves from {display(start, language)} to {display(end, language)}{suffix}: "
            f"{display(abs(delta), language)}% {'higher' if delta > 0 else 'lower'}. "
            "Observed intervals may be incomplete."
        )
    top = usable["value"].max()
    leaders = usable.loc[usable["value"] == top]
    if len(leaders) == len(usable) and len(usable) > 1:
        return (
            f"Las {len(usable)} categorías tienen el mismo valor: {display(top, language)}."
            if spanish
            else f"All {len(usable)} categories have the same value: {display(top, language)}."
        )
    groups = [c for c in data.columns if c != "value"]
    names = [
        " / ".join(display(row[c], language)[:65] for c in groups) for _, row in leaders.head(2).iterrows()
    ]
    label = ", ".join(names)
    if len(leaders) > 2:
        label += f" +{len(leaders) - 2}"
    suffix = f" {spec.unit}" if spec.unit else ""
    text = (
        (
            f"{label} reúne {display(top, language)} registros."
            if spec.aggregation == "count_rows"
            else f"{label} encabeza la comparación con {display(top, language)}{suffix}."
        )
        if spanish
        else (
            f"{label} accounts for {display(top, language)} records."
            if spec.aggregation == "count_rows"
            else f"{label} leads the comparison with {display(top, language)}{suffix}."
        )
    )
    if len(leaders) > 1:
        noun = (" registros" if spanish else " records") if spec.aggregation == "count_rows" else suffix
        text = (
            f"{label} comparten el primer puesto: {display(top, language)}{noun} cada uno."
            if spanish
            else f"{label} share the lead: {display(top, language)}{noun} each."
        )
    # Shares are meaningful only for additive, nonnegative metrics with complete group values.
    total = float(usable["value"].sum())
    if (
        spec.aggregation in {"count_rows", "count_non_null", "sum"}
        and valid.all()
        and (usable["value"] >= 0).all()
        and total > 0
    ):
        share = display(float(top) / total * 100, language)
        text += (
            (
                f" Representa el {share} % del total."
                if len(leaders) == 1
                else f" Cada categoría indicada representa el {share} % del total."
            )
            if spanish
            else (
                f" It accounts for {share}% of the total."
                if len(leaders) == 1
                else f" Each named category accounts for {share}% of the total."
            )
        )
    if not valid.all():
        text += (
            " Comparación entre grupos con valor disponible."
            if spanish
            else "Comparison uses groups with available values."
        )
    return text
