"""Print-friendly chart components with consistent typography and localized labels."""

import io
import textwrap

import matplotlib

matplotlib.use("Agg")
import pandas as pd
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter, MaxNLocator

from app.core.settings import ReportError
from app.reporting.localization import TEXT, display, metric_label
from app.schemas.config import Chart


def render_chart(
    data: pd.DataFrame,
    spec: Chart,
    accent: str,
    labels: dict[str, str],
    language: str = "en",
    show_title: bool = True,
    wide: bool = False,
    aspect_ratio: float | None = None,
) -> bytes:
    figure_height = 8 * aspect_ratio if aspect_ratio is not None else (2.6 if wide else 2.9)
    figure = Figure(figsize=(8, figure_height), dpi=170, layout="constrained")
    axis = figure.subplots()
    groups = [c for c in data.columns if c != "value"]
    values = pd.to_numeric(data["value"], errors="coerce")

    def category(value):
        if isinstance(value, pd.Timestamp):
            if spec.time_granularity in {"month", "quarter"}:
                months = (
                    "ene feb mar abr may jun jul ago sep oct nov dic"
                    if language == "es"
                    else "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec"
                ).split()
                return f"{months[value.month - 1]} {value.year}"
            if spec.time_granularity == "year":
                return str(value.year)
        return TEXT[language]["unknown"] if str(value) == "Unknown" else display(value, language)

    names = data[groups].apply(lambda row: " / ".join(category(v) for v in row), axis=1)
    names = names.map(lambda value: textwrap.fill(value[:65] + ("…" if len(value) > 65 else ""), width=24))
    valid = values.notna()
    ink, muted, line = "#132B42", "#536779", "#E1E8EF"
    if not valid.any():
        axis.text(0.5, 0.5, TEXT[language]["no_values"], color=muted, ha="center", va="center")
        axis.set_axis_off()
    elif spec.type in {"pie", "donut"}:
        if (values[valid] < 0).any():
            raise ReportError("Pie and donut charts require nonnegative values")
        if values[valid].sum() == 0:
            axis.text(0.5, 0.5, TEXT[language]["zero_values"], color=muted, ha="center", va="center")
            axis.set_axis_off()
        else:
            palette = [accent, "#18344D", "#498C91", "#8DA8C0", "#BDCCD9", "#778895"]
            wedges, _ = axis.pie(
                values[valid],
                startangle=90,
                counterclock=False,
                colors=[palette[i % len(palette)] for i in range(len(values[valid]))],
                textprops={"fontsize": 9, "fontweight": "bold", "color": "white"},
                wedgeprops={
                    "width": 0.34 if spec.type == "donut" else 1,
                    "edgecolor": "white",
                    "linewidth": 2,
                },
            )
            legend = [
                f"{n}   {display(v, language)} · {display(v / values[valid].sum() * 100, language, 1)}%"
                for n, v in zip(names[valid], values[valid], strict=True)
            ]
            axis.legend(
                wedges,
                legend,
                loc="center left",
                bbox_to_anchor=(1, 0.5),
                frameon=False,
                fontsize=9,
                labelspacing=1.2,
                handlelength=1,
                labelcolor=ink,
            )
            if spec.type == "donut":
                axis.text(
                    0,
                    0.05,
                    display(values[valid].sum(), language),
                    ha="center",
                    va="center",
                    color=ink,
                    fontsize=20,
                    fontweight="bold",
                )
                axis.text(
                    0,
                    -0.16,
                    TEXT[language]["value"]
                    if spec.aggregation != "count_rows"
                    else TEXT[language]["records"],
                    ha="center",
                    color=muted,
                    fontsize=8,
                )
    else:
        positions = list(range(len(names)))
        horizontal = spec.type == "horizontal_bar"
        label = metric_label(spec.aggregation, spec.column, labels, language)
        if spec.unit:
            label += f" ({spec.unit})"
        if horizontal:
            bars = axis.barh(positions, values, color=accent, height=0.55)
            axis.set_yticks(positions, names, fontsize=9)
            axis.invert_yaxis()
            axis.set_xlabel(label, fontsize=8, labelpad=9, color=muted)
            axis.bar_label(
                bars,
                labels=[display(v, language) if pd.notna(v) else "" for v in values],
                padding=6,
                fontsize=9,
                color=ink,
            )
            axis.margins(x=0.18)
        elif spec.type == "line":
            axis.plot(positions, values, color=accent, marker="o", markersize=5, linewidth=2.2)
            axis.fill_between(positions, values.to_numpy(dtype=float), alpha=0.06, color=accent)
            axis.set_xticks(positions, names, fontsize=8)
            axis.set_ylabel(label, fontsize=8, labelpad=10, color=muted)
            if len(values) <= 10:
                for position, value in zip(positions, values, strict=True):
                    if pd.notna(value):
                        axis.annotate(
                            display(value, language),
                            (position, value),
                            xytext=(0, 9),
                            textcoords="offset points",
                            ha="center",
                            fontsize=8,
                            color=ink,
                        )
            axis.margins(y=0.25)
        else:
            bars = axis.bar(positions, values, color=accent, width=0.55)
            axis.set_xticks(
                positions,
                names,
                rotation=0 if len(names) <= 5 else 25,
                ha="center" if len(names) <= 5 else "right",
                fontsize=8,
            )
            axis.set_ylabel(label, fontsize=8, labelpad=10, color=muted)
            if len(values) <= 12:
                axis.bar_label(
                    bars,
                    labels=[display(v, language) if pd.notna(v) else "" for v in values],
                    padding=5,
                    fontsize=9,
                    color=ink,
                )
            axis.margins(y=0.18)
        numeric_axis = axis.xaxis if horizontal else axis.yaxis
        numeric_axis.set_major_locator(
            MaxNLocator(
                nbins=5, integer=spec.aggregation in {"count_rows", "count_non_null", "distinct_count"}
            )
        )
        numeric_axis.set_major_formatter(FuncFormatter(lambda value, _: display(float(value), language)))
        axis.spines[["top", "right", "left"]].set_visible(False)
        axis.spines["bottom"].set_color(line)
        axis.tick_params(axis="both", length=0, colors=muted, pad=7)
        axis.grid(axis="x" if horizontal else "y", color=line, linewidth=0.7)
        axis.set_axisbelow(True)
    if show_title:
        axis.set_title(spec.title[:120], loc="left", fontsize=12, fontweight="bold", color=ink, pad=15)
    stream = io.BytesIO()
    figure.savefig(stream, format="png", facecolor="white")
    figure.clear()
    return stream.getvalue()
