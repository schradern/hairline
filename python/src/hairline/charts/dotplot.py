"""Dot plot with intervals: sorted by value, labels on the left, the value on the right."""

from __future__ import annotations

import pandas as pd

from hairline.charts.common import check_columns, check_numeric, humanise, labels_with_n
from hairline.charts.forest import forest_spec
from hairline.charts.forest_geometry import forest_drawing
from hairline.drawing import fit_height
from hairline.figure import HairlineFigure, figure
from hairline.marks import lone_color
from hairline.numbers import word
from hairline.settings import current_settings


def dotplot(data: pd.DataFrame, label: str, estimate: str, low: str | None = None, high: str | None = None, *,
            title: str | None = None, subtitle: str | None = None, caption: str | None = None, sort: bool = True,
            ratio: bool = False, reference: float | None = None, digits: int | None = None,
            size: str = "onehalf", n: str | None = None, percent: bool = False) -> HairlineFigure:
    """One dot per row, largest at the top; with `low` and `high` an interval and its numbers on the right.
    `reference` draws a vertical line (a target or a null value). `n` names the column holding each row's n,
    written after its label in the locale ("Medical (n = 1,010)"). `percent=True` draws shares (0.15) as percent
    (15), the heading naming the unit."""
    check_columns(data, [label, estimate, low, high, n])
    if (low is None) != (high is None):
        raise ValueError(f"hairline: dotplot: an interval needs both low and high; got only "
                         f"{'low' if low is not None else 'high'}={low if low is not None else high!r}")
    interval = low is not None and high is not None
    data = as_percent(data, [estimate, low, high]) if percent else data
    rows = data.sort_values(estimate, ascending=False, kind="mergesort") if sort else data
    if n is not None:
        check_numeric(rows, [n], "dotplot")
        names = [str(name) for name in rows[label]]
        rows = rows.assign(**{label: labels_with_n(names, dict(zip(names, rows[n], strict=True)),
                                                    current_settings().locale)})
    if not interval:
        rows = rows.assign(_low=rows[estimate], _high=rows[estimate])
        low, high = "_low", "_high"
    name = f"{humanise(estimate)} (%)" if percent else humanise(estimate)
    heading = word("interval", name=name) if interval else name
    spec = forest_spec(rows, label, estimate, low, high, ratio=ratio, color=lone_color(),
                       study_heading=humanise(label), effect_heading=heading, digits=digits, marker="dot",
                       interval=interval, null=reference)
    result = figure(title or f"{humanise(estimate)} by {str(label).replace('_', ' ')}", subtitle=subtitle,
                    caption=caption, size=size)
    result.draw(0, lambda box, measure, style: forest_drawing(spec, box, measure, style))
    return fit_height(result)


def as_percent(data: pd.DataFrame, columns: list[str | None]) -> pd.DataFrame:
    """Shares as percent: each named column × 100."""
    check_numeric(data, [column for column in columns if column], "dotplot")
    return data.assign(**{column: data[column] * 100 for column in columns if column})
